from __future__ import annotations
from datetime import datetime, timedelta, timezone

def fresh(source: str, observation: dict[str, object], observed_at: datetime, max_age_seconds: int = 300) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {"source": source, "observation": observation, "fresh": observed_at >= now - timedelta(seconds=max_age_seconds), "observed_at": observed_at}
