from __future__ import annotations

from aegis.domain.catalog import product
from aegis.domain.inventory import InventoryService
from aegis.domain.queue import OrderQueue
from aegis.types import new_id


class OrderService:
    def __init__(self, inventory: InventoryService, queue: OrderQueue) -> None:
        self.inventory = inventory; self.queue = queue; self.orders: dict[str, dict[str, object]] = {}; self.idempotency: dict[str, str] = {}
    def create(self, sku: str, quantity: int, idempotency_key: str) -> dict[str, object]:
        if idempotency_key in self.idempotency: return self.orders[self.idempotency[idempotency_key]]
        item = product(sku)
        if item is None: raise ValueError("product does not exist")
        order_id = new_id(); reservation = self.inventory.reserve(sku, quantity, order_id)
        order = {"order_id": order_id, "sku": sku, "quantity": quantity, "total_minor": item.price_minor * quantity, "currency": item.currency, "state": "QUEUED", "reservation_id": reservation["reservation_id"]}
        self.orders[order_id] = order; self.idempotency[idempotency_key] = order_id; self.queue.submit(order_id)
        return order
    def complete_next(self) -> dict[str, object] | None:
        job = self.queue.claim()
        if job is None: return None
        order = self.orders[str(job["order_id"])]
        self.inventory.commit(str(order["reservation_id"])); order["state"] = "COMPLETED"; job["state"] = "COMPLETED"
        return order
