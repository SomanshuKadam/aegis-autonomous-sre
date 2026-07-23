from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from aegis.domain.catalog import browse, product
from aegis.domain.commerce_store import CommerceStore

router = APIRouter(prefix="/api/v1", tags=["commerce"])
orders = CommerceStore()

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
def create_order(payload: OrderInput, idempotency_key: str = Header(alias="Idempotency-Key")) -> dict[str, object]:
    if not idempotency_key: raise HTTPException(status_code=400, detail="Idempotency-Key is required")
    item = product(payload.sku)
    if item is None: raise HTTPException(status_code=404, detail="product does not exist")
    return orders.create_order({"sku": payload.sku, "quantity": payload.quantity, "total_minor": item.price_minor * payload.quantity, "currency": item.currency}, idempotency_key)

@router.get("/orders/{order_id}")
def get_order(order_id: str) -> dict[str, object]:
    return orders.get_order(order_id)

@router.post("/reservations", status_code=201)
def create_reservation(payload: ReservationInput) -> dict[str, object]:
    raise HTTPException(status_code=410, detail="inventory reservations are handled by the inventory service")

@router.post("/orders/process-next")
def process_next() -> dict[str, object]:
    completed = orders.complete_next()
    return {"order": completed, "processed": completed is not None}
