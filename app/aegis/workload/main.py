import asyncio
import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aegis.workload.service import WorkloadService

service = WorkloadService(os.getenv("AEGIS_WORKLOAD_STATE_PATH", "/tmp/aegis-workload-runs.json"))
state = {"run_id": None, "failures": 0, "running": True}

async def generate() -> None:
    if not os.getenv("AEGIS_NORMAL_WORKLOAD_ENABLED", "true").lower() == "true":
        return
    run = service.start(seed=int(os.getenv("AEGIS_WORKLOAD_SEED", "1")))
    state["run_id"] = run.run_id
    url = os.getenv("AEGIS_API_URL", "http://api:8081")
    async with httpx.AsyncClient(timeout=5) as client:
        while state["running"]:
            try:
                await client.post(f"{url}/api/v1/orders", json={"sku": "sku-001", "quantity": 1}, headers={"Idempotency-Key": f"workload-{run.run_id}-{run.generated_orders}"})
                service.record_order(run.run_id)
            except Exception:
                state["failures"] += 1
            await asyncio.sleep(float(os.getenv("AEGIS_WORKLOAD_INTERVAL_SECONDS", "5")))

@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(generate())
    yield
    state["running"] = False
    task.cancel()

app = FastAPI(title="Aegis Workload", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "service": "aegis-workload", **state}
