import asyncio
import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException
from aegis.config import get_settings
from aegis.domain.commerce_store import CommerceStore
from aegis.control.service_state import ServiceState

state = {"processed": 0, "failures": 0, "running": True}
capacity = ServiceState("worker", {"desired": 1, "previous": 1, "maximum": 4})
commerce = CommerceStore()

async def consume() -> None:
    url = os.getenv("AEGIS_API_URL", "http://api:8081")
    async with httpx.AsyncClient(timeout=5) as client:
        while state["running"]:
            try:
                result = (await client.post(f"{url}/api/v1/orders/process-next")).json()
                state["processed"] += int(bool(result.get("processed")))
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
    return {"status": "ok", "service": "aegis-worker", **state, **queue, "capacity": current["desired"], "maximum": current["maximum"], "resource_headroom": current["desired"] < current["maximum"]}

@app.post("/control/capacity")
def set_capacity(desired: int, authorization: str | None = Header(default=None), x_aegis_rollback: str | None = Header(default=None)) -> dict[str, object]:
    if authorization != f"Bearer {get_settings().runner_token.get_secret_value()}": raise HTTPException(status_code=401, detail="invalid runner credentials")
    current = capacity.read()
    rollback = x_aegis_rollback == "true"
    allowed = 1 <= desired <= current["maximum"] if rollback else current["desired"] < desired <= current["maximum"]
    if not allowed: raise HTTPException(status_code=422, detail="worker capacity is outside the registered action bounds")
    return {**capacity.update_capacity(desired), "state": "SUCCEEDED", "rollback": rollback}
