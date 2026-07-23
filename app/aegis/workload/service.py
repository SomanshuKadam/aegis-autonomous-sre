from __future__ import annotations

from dataclasses import dataclass, field

from pymongo import ReturnDocument

from aegis.integrations.mongodb import MongoStore
from aegis.types import utc_now


@dataclass
class WorkloadRun:
    run_id: str
    seed: int
    enabled: bool
    demo: bool = False
    profile_id: str = "normal"
    generated_orders: int = 0
    condition_markers: dict[str, object] = field(default_factory=dict)


class WorkloadService:
    """Mongo-backed workload profiles with stable run identities and one-shot markers."""

    def __init__(self, _: str | None = None) -> None:
        from aegis.config import get_settings
        self.collection = MongoStore(get_settings()).db["workload_runs"]
        self.collection.create_index("run_id", unique=True)

    def start(self, seed: int = 1, demo: bool = False, run_id: str | None = None) -> WorkloadRun:
        profile_id = "demo" if demo else "normal"
        identity = run_id or f"{profile_id}-local"
        value = self.collection.find_one_and_update(
            {"run_id": identity},
            {"$setOnInsert": {"run_id": identity, "seed": seed, "demo": demo, "profile_id": profile_id, "enabled": True, "generated_orders": 0, "condition_markers": {}, "started_at": utc_now()}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return self._run(value)

    def stop(self, run_id: str) -> WorkloadRun:
        value = self.collection.find_one_and_update({"run_id": run_id}, {"$set": {"enabled": False, "stopped_at": utc_now()}}, return_document=ReturnDocument.AFTER)
        if value is None:
            raise KeyError(run_id)
        return self._run(value)

    def record_order(self, run_id: str) -> WorkloadRun:
        value = self.collection.find_one_and_update({"run_id": run_id, "enabled": True}, {"$inc": {"generated_orders": 1}, "$set": {"updated_at": utc_now()}}, return_document=ReturnDocument.AFTER)
        if value is None:
            raise KeyError(run_id)
        return self._run(value)

    def mark_condition_once(self, run_id: str, condition: str) -> bool:
        value = self.collection.find_one_and_update(
            {"run_id": run_id, f"condition_markers.{condition}": {"$exists": False}},
            {"$set": {f"condition_markers.{condition}": {"state": "EXPOSED", "at": utc_now()}}},
            return_document=ReturnDocument.AFTER,
        )
        return value is not None

    def get(self, run_id: str) -> WorkloadRun | None:
        value = self.collection.find_one({"run_id": run_id})
        return self._run(value) if value else None

    @staticmethod
    def _run(value: dict[str, object]) -> WorkloadRun:
        return WorkloadRun(run_id=str(value["run_id"]), seed=int(value["seed"]), enabled=bool(value["enabled"]), demo=bool(value.get("demo", False)), profile_id=str(value.get("profile_id", "normal")), generated_orders=int(value.get("generated_orders", 0)), condition_markers=dict(value.get("condition_markers", {})))
