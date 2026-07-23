import asyncio
import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI

state = {"processed": 0, "failures": 0, "running": True}

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
    return {"status": "ok", "service": "aegis-worker", **state}
