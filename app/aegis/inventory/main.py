from fastapi import FastAPI, Header, HTTPException
from time import perf_counter
from pydantic import BaseModel, Field
from aegis.config import get_settings
from aegis.inventory.store import InventoryStore

app = FastAPI(title="Aegis Inventory")
inventory = InventoryStore()
capacity = {"desired": 1, "previous": 1, "healthy": True}

class ReservationRequest(BaseModel):
    sku: str
    quantity: int = Field(ge=1, le=20)
    order_id: str


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok" if capacity["healthy"] else "degraded", "service": "aegis-inventory", "capacity": capacity["desired"]}

@app.post("/reservations")
def reserve(payload: ReservationRequest, traceparent: str | None = Header(default=None)) -> dict[str, object]:
    started = perf_counter()
    reservation = inventory.reserve(payload.sku, payload.quantity, payload.order_id)
    return {**reservation, "trace_context_received": bool(traceparent), "latency_ms": round((perf_counter() - started) * 1000, 3), "capacity": capacity["desired"]}

@app.post("/reservations/{reservation_id}/commit")
def commit(reservation_id: str) -> dict[str, object]:
    return inventory.commit(reservation_id)

@app.post("/control/capacity")
def set_capacity(desired: int, authorization: str | None = Header(default=None)) -> dict[str, object]:
    if authorization != f"Bearer {get_settings().runner_token.get_secret_value()}": raise HTTPException(status_code=401, detail="invalid runner credentials")
    if not 1 <= desired <= 4: raise HTTPException(status_code=422, detail="capacity is outside the approved range")
    capacity["previous"] = capacity["desired"]; capacity["desired"] = desired
    return {**capacity, "state": "SUCCEEDED"}
