from fastapi import FastAPI, Header
from pydantic import BaseModel, Field
from aegis.domain.inventory import InventoryService

app = FastAPI(title="Aegis Inventory")
inventory = InventoryService()

class ReservationRequest(BaseModel):
    sku: str
    quantity: int = Field(ge=1, le=20)
    order_id: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aegis-inventory"}

@app.post("/reservations")
def reserve(payload: ReservationRequest, traceparent: str | None = Header(default=None)) -> dict[str, object]:
    reservation = inventory.reserve(payload.sku, payload.quantity, payload.order_id)
    return {**reservation, "trace_context_received": bool(traceparent)}
