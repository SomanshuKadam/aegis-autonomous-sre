from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from aegis.domain.catalog import browse, product
from aegis.domain.inventory import InventoryService
from aegis.domain.orders import OrderService
from aegis.domain.queue import OrderQueue

router = APIRouter(prefix="/api/v1", tags=["commerce"])
inventory = InventoryService(); orders = OrderService(inventory, OrderQueue())

class OrderInput(BaseModel):
    sku: str
    quantity: int = Field(ge=1, le=20)

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
    return orders.create(payload.sku, payload.quantity, idempotency_key)

@router.post("/orders/process-next")
def process_next() -> dict[str, object]:
    completed = orders.complete_next()
    return {"order": completed, "processed": completed is not None}
