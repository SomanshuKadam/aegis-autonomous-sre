from __future__ import annotations

from datetime import timedelta

from pymongo import ReturnDocument

from aegis.integrations.mongodb import MongoStore
from aegis.types import new_id, utc_now


class InventoryStore:
    def __init__(self) -> None:
        from aegis.config import get_settings
        store = MongoStore(get_settings())
        self.db = store.db
        self.stock = self.db["inventory"]
        self.reservations = self.db["reservations"]
        if self.stock.count_documents({}) == 0:
            self.stock.insert_many([{"sku": "sku-001", "available": 100}, {"sku": "sku-002", "available": 100}])

    def reserve(self, sku: str, quantity: int, order_id: str) -> dict[str, object]:
        stock = self.stock.find_one_and_update({"sku": sku, "available": {"$gte": quantity}}, {"$inc": {"available": -quantity}}, return_document=ReturnDocument.AFTER)
        if stock is None:
            raise ValueError("inventory is unavailable")
        reservation = {"reservation_id": new_id(), "sku": sku, "order_id": order_id, "quantity": quantity, "state": "HELD", "expires_at": utc_now() + timedelta(minutes=10), "created_at": utc_now()}
        self.reservations.insert_one(reservation)
        reservation.pop("_id", None)
        return reservation

    def commit(self, reservation_id: str) -> dict[str, object]:
        reservation = self.reservations.find_one_and_update({"reservation_id": reservation_id, "state": "HELD"}, {"$set": {"state": "COMMITTED", "committed_at": utc_now()}}, return_document=ReturnDocument.AFTER)
        if reservation is None:
            raise KeyError(reservation_id)
        reservation.pop("_id", None)
        return reservation
