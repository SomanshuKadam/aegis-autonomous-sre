from __future__ import annotations
from datetime import datetime, timedelta, timezone

def fresh(source: str, observation: dict[str, object], observed_at: datetime, max_age_seconds: int = 300) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {"source": source, "observation": observation, "fresh": observed_at >= now - timedelta(seconds=max_age_seconds), "observed_at": observed_at}

class ReadOnlyEvidence:
    """Bounded adapters that expose observations only and never accept executable queries."""
    def service_health(self, service: str, healthy: bool) -> dict[str, object]:
        return fresh("service-health", {"service": service, "healthy": healthy}, datetime.now(timezone.utc))
    def mongo_state(self, database: str, collection: str, index_present: bool) -> dict[str, object]:
        return fresh("mongo-state", {"database": database, "collection": collection, "index_present": index_present}, datetime.now(timezone.utc))
    def unavailable(self, source: str, reason: str) -> dict[str, object]:
        return {"source": source, "observation": {"reason": reason}, "fresh": False, "unavailable": True, "observed_at": datetime.now(timezone.utc)}
