from fastapi import FastAPI, Header
from time import perf_counter
from pydantic import BaseModel, Field
from aegis.domain.inventory import InventoryService

app = FastAPI(title="Aegis Inventory")
inventory = InventoryService()
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
