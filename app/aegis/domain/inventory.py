from __future__ import annotations

from datetime import timedelta

from aegis.types import new_id, utc_now


class InventoryService:
    def __init__(self) -> None:
        self.available = {"sku-001": 25, "sku-002": 25}
        self.holds: dict[str, dict[str, object]] = {}

    def reserve(self, sku: str, quantity: int, order_id: str) -> dict[str, object]:
        if quantity < 1 or self.available.get(sku, 0) < quantity:
            raise ValueError("inventory is unavailable")
        self.available[sku] -= quantity
        reservation = {"reservation_id": new_id(), "sku": sku, "order_id": order_id, "quantity": quantity, "state": "HELD", "expires_at": utc_now() + timedelta(minutes=10)}
        self.holds[str(reservation["reservation_id"])] = reservation
        return reservation

    def commit(self, reservation_id: str) -> dict[str, object]:
        reservation = self.holds[reservation_id]
        reservation["state"] = "COMMITTED"
        return reservation

    def release(self, reservation_id: str) -> dict[str, object]:
        reservation = self.holds[reservation_id]
        if reservation["state"] == "HELD":
            self.available[str(reservation["sku"])] += int(reservation["quantity"])
            reservation["state"] = "RELEASED"
        return reservation
