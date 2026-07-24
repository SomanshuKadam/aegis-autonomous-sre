import asyncio
import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException
from opentelemetry import trace
from aegis.config import get_settings
from aegis.domain.commerce_store import CommerceStore
from aegis.control.service_state import ServiceState

state = {"processed": 0, "failures": 0, "running": True}
capacity = ServiceState("worker", {"desired": 1, "previous": 1, "maximum": 4})
commerce = CommerceStore()
tracer = trace.get_tracer("aegis.worker")

async def consume() -> None:
    url = os.getenv("AEGIS_API_URL", "http://api:8081")
    async with httpx.AsyncClient(timeout=5) as client:
        while state["running"]:
            try:
                desired = int(capacity.read()["desired"])
                responses = await asyncio.gather(*[client.post(f"{url}/api/v1/orders/process-next") for _ in range(desired)])
                state["processed"] += sum(int(bool(response.json().get("processed"))) for response in responses)
            except Exception:
                state["failures"] += 1
            await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(consume())
    yield
    state["running"] = False
    task.cancel()

app = FastAPI(title="Aegis Order Worker", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, object]:
    queue = commerce.queue_health()
    current = capacity.read()
    backlog = int(queue["queue_depth"]) > 0 and int(queue["oldest_age_seconds"]) >= 30
    evidence_name = "aegis.evidence.order_backlog" if backlog else "aegis.evidence.order_queue_healthy"
    with tracer.start_as_current_span(evidence_name) as evidence_span:
        evidence_span.set_attribute("aegis.evidence.source", "live_order_queue_state")
        evidence_span.set_attribute("queue.depth", int(queue["queue_depth"]))
        evidence_span.set_attribute("queue.oldest_age_seconds", int(queue["oldest_age_seconds"]))
        evidence_span.set_attribute("worker.capacity", int(current["desired"]))
        evidence_span.set_attribute("worker.maximum", int(current["maximum"]))
        evidence_span.set_attribute("worker.healthy", True)
        evidence_span.set_attribute("worker.resource_headroom", int(current["desired"]) < int(current["maximum"]))
    return {"status": "ok", "service": "aegis-worker", **state, **queue, "capacity": current["desired"], "maximum": current["maximum"], "resource_headroom": current["desired"] < current["maximum"]}

@app.post("/control/capacity")
def set_capacity(desired: int, authorization: str | None = Header(default=None), x_aegis_rollback: str | None = Header(default=None)) -> dict[str, object]:
    if authorization != f"Bearer {get_settings().runner_token.get_secret_value()}": raise HTTPException(status_code=401, detail="invalid runner credentials")
    current = capacity.read()
    rollback = x_aegis_rollback == "true"
    allowed = 1 <= desired <= current["maximum"] if rollback else current["desired"] < desired <= current["maximum"]
    if not allowed: raise HTTPException(status_code=422, detail="worker capacity is outside the registered action bounds")
    return {**capacity.update_capacity(desired), "state": "SUCCEEDED", "rollback": rollback}
