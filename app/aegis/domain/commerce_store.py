from __future__ import annotations

from datetime import timedelta

from pymongo import ASCENDING, ReturnDocument

from aegis.integrations.mongodb import MongoStore
from aegis.types import new_id, utc_now


class CommerceStore:
    """Mongo-backed order and queue state shared by API and worker processes."""

    def __init__(self) -> None:
        from aegis.config import get_settings
        store = MongoStore(get_settings())
        self.db = store.db
        store.bootstrap()
        self.orders = self.db["orders"]
        self.jobs = self.db["queue_jobs"]
        self.orders.create_index("idempotency_key", unique=True)
        self.jobs.create_index([("state", ASCENDING), ("available_at", ASCENDING)])

    def create_order(self, order: dict[str, object], idempotency_key: str) -> dict[str, object]:
        existing = self.orders.find_one({"idempotency_key": idempotency_key})
        if existing:
            return self._document(existing)
        order_id = str(order.get("order_id") or new_id())
        document = {**order, "order_id": order_id, "idempotency_key": idempotency_key, "state": "QUEUED", "created_at": utc_now(), "updated_at": utc_now()}
        self.orders.insert_one(document)
        self.jobs.insert_one({"job_id": new_id(), "order_id": order_id, "state": "PENDING", "attempts": 0, "available_at": utc_now(), "created_at": utc_now(), "trace_context": document.get("trace_context")})
        return self._document(document)

    def get_order_by_idempotency(self, idempotency_key: str) -> dict[str, object] | None:
        result = self.orders.find_one({"idempotency_key": idempotency_key})
        return self._document(result) if result else None

    def get_order(self, order_id: str) -> dict[str, object]:
        result = self.orders.find_one({"order_id": order_id})
        if result is None:
            raise KeyError(order_id)
        return self._document(result)

    def complete_next(self) -> dict[str, object] | None:
        now = utc_now()
        self.jobs.update_many({"state": "CLAIMED", "lease_until": {"$lt": now}}, {"$set": {"state": "PENDING", "available_at": now}})
        job = self.jobs.find_one_and_update({"state": "PENDING", "available_at": {"$lte": now}}, {"$set": {"state": "CLAIMED", "lease_until": now + timedelta(seconds=30), "claimed_at": now}, "$inc": {"attempts": 1}}, sort=[("available_at", ASCENDING)], return_document=ReturnDocument.AFTER)
        if job is None:
            return None
        order = self.orders.find_one_and_update({"order_id": job["order_id"]}, {"$set": {"state": "COMPLETED", "updated_at": utc_now()}}, return_document=ReturnDocument.AFTER)
        self.jobs.update_one({"job_id": job["job_id"]}, {"$set": {"state": "COMPLETED", "completed_at": utc_now()}})
        return self._document(order)

    def queue_health(self) -> dict[str, object]:
        now = utc_now(); pending = list(self.jobs.find({"state": "PENDING"}))
        oldest = min((item["created_at"] for item in pending), default=now)
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=now.tzinfo)
        return {"queue_depth": len(pending), "oldest_age_seconds": max(0, int((now - oldest).total_seconds()))}

    @staticmethod
    def _document(value: dict[str, object] | None) -> dict[str, object]:
        if value is None:
            raise KeyError("order was not found")
        value.pop("_id", None)
        return value
