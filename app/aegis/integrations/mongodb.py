from __future__ import annotations
from pymongo import ASCENDING, MongoClient
from aegis.config import Settings

COLLECTIONS = ("products", "inventory", "orders", "queue_jobs", "workload_runs", "incidents", "alerts", "timeline", "evidence", "hypotheses", "proposals", "policy_decisions", "approvals", "executions", "verifications", "rollbacks", "notifications")
class MongoStore:
    def __init__(self, settings: Settings): self.client = MongoClient(settings.mongodb_uri.get_secret_value(), serverSelectionTimeoutMS=5000); self.db = self.client[settings.mongo_database]
    def health(self) -> bool: return bool(self.client.admin.command("ping").get("ok"))
    def bootstrap(self) -> None:
        self.db.incidents.create_index("dedup_key", unique=True)
        self.db.timeline.create_index([("incident_id", ASCENDING), ("sequence", ASCENDING)], unique=True)
        self.db.orders.create_index("idempotency_key", unique=True)
        self.db.executions.create_index("idempotency_key", unique=True)
        self.db.queue_jobs.create_index([("state", ASCENDING), ("available_at", ASCENDING)])
        self.db.alerts.create_index([("source", ASCENDING), ("fingerprint", ASCENDING), ("received_at", ASCENDING)])
