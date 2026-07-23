from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
import httpx
from pydantic import BaseModel, Field

from aegis.domain.catalog import browse, product
from aegis.domain.commerce_store import CommerceStore
from aegis.config import get_settings
from aegis.types import new_id

router = APIRouter(prefix="/api/v1", tags=["commerce"])
orders = CommerceStore()
settings = get_settings()

class OrderInput(BaseModel):
    sku: str
    quantity: int = Field(ge=1, le=20)

class ReservationInput(BaseModel):
    sku: str
    quantity: int = Field(ge=1, le=20)
    order_id: str = Field(min_length=1)

@router.get("/products")
def products(q: str | None = None) -> dict[str, object]: return {"items": [item.model_dump() for item in browse(q)]}

@router.get("/products/{sku}")
def get_product(sku: str) -> dict[str, object]:
    item = product(sku)
    if item is None: raise HTTPException(status_code=404, detail="product not found")
    return item.model_dump()

@router.post("/orders", status_code=201)
def create_order(payload: OrderInput, idempotency_key: str = Header(alias="Idempotency-Key"), traceparent: str | None = Header(default=None)) -> dict[str, object]:
    if not idempotency_key: raise HTTPException(status_code=400, detail="Idempotency-Key is required")
    item = product(payload.sku)
    if item is None: raise HTTPException(status_code=404, detail="product does not exist")
    existing = orders.get_order_by_idempotency(idempotency_key)
    if existing: return existing
    order_id = new_id()
    headers = {"traceparent": traceparent} if traceparent else {}
    reservation = httpx.post(f"{settings.inventory_url.rstrip('/')}/reservations", headers=headers, json={"sku": payload.sku, "quantity": payload.quantity, "order_id": order_id}, timeout=10)
    if reservation.status_code >= 400: raise HTTPException(status_code=409, detail="inventory reservation failed")
    return orders.create_order({"order_id": order_id, "sku": payload.sku, "quantity": payload.quantity, "total_minor": item.price_minor * payload.quantity, "currency": item.currency, "reservation_id": reservation.json()["reservation_id"], "trace_context": traceparent, "trace_context_forwarded": bool(reservation.json().get("trace_context_received"))}, idempotency_key)

@router.get("/orders/{order_id}")
def get_order(order_id: str) -> dict[str, object]:
    return orders.get_order(order_id)

@router.post("/reservations", status_code=201)
def create_reservation(payload: ReservationInput) -> dict[str, object]:
    raise HTTPException(status_code=410, detail="inventory reservations are handled by the inventory service")

@router.post("/orders/process-next")
def process_next() -> dict[str, object]:
    completed = orders.complete_next()
    if completed and completed.get("reservation_id"):
        headers = {"traceparent": str(completed["trace_context"])} if completed.get("trace_context") else {}
        response = httpx.post(f"{settings.inventory_url.rstrip('/')}/reservations/{completed['reservation_id']}/commit", headers=headers, timeout=10)
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail="inventory commit failed")
    return {"order": completed, "processed": completed is not None}
