import asyncio
import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException
from aegis.config import get_settings

state = {"processed": 0, "failures": 0, "running": True}
capacity = {"desired": 1, "previous": 1, "maximum": 4}

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
    return {"status": "ok", "service": "aegis-worker", **state, "queue_depth": 0, "oldest_age_seconds": 0, "capacity": capacity["desired"], "resource_headroom": capacity["desired"] < capacity["maximum"]}

@app.post("/control/capacity")
def set_capacity(desired: int, authorization: str | None = Header(default=None)) -> dict[str, object]:
    if authorization != f"Bearer {get_settings().runner_token.get_secret_value()}": raise HTTPException(status_code=401, detail="invalid runner credentials")
    if not capacity["desired"] < desired <= capacity["maximum"]: raise HTTPException(status_code=422, detail="worker capacity must increase within the approved range")
    capacity["previous"] = capacity["desired"]; capacity["desired"] = desired
    return {**capacity, "state": "SUCCEEDED"}
