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
        self.operations = self.db["inventory_operations"]
        for sku in ("sku-001", "sku-002"):
            self.stock.update_one(
                {"sku": sku},
                {"$setOnInsert": {"sku": sku, "available": 10000, "provisioned_for": "continuous_local_workload"}},
                upsert=True,
            )
        # Local normal traffic is intentionally continuous. Restore only exhausted seed stock on
        # startup so normal-mode telemetry does not turn into a stock-out failure demonstration.
        self.stock.update_many({"available": {"$lt": 1000}}, {"$set": {"available": 10000, "provisioned_for": "continuous_local_workload"}})

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

    def record_operation(self, success: bool, latency_ms: float, reason: str = "") -> None:
        self.operations.insert_one({"success": success, "latency_ms": latency_ms, "reason": reason, "occurred_at": utc_now()})

    def metrics(self, window_seconds: int = 5) -> dict[str, object]:
        since = utc_now() - timedelta(seconds=window_seconds)
        entries = list(self.operations.find({"occurred_at": {"$gte": since}}, {"_id": 0}))
        total = len(entries)
        failures = sum(not bool(entry["success"]) for entry in entries)
        latencies = sorted(float(entry["latency_ms"]) for entry in entries)
        p95_index = max(0, int(len(latencies) * 0.95) - 1)
        return {"window_seconds": window_seconds, "requests": total, "failures": failures, "error_rate": round(failures / total, 4) if total else 0.0, "p95_latency_ms": latencies[p95_index] if latencies else 0.0}
