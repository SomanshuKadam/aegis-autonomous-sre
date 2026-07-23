from __future__ import annotations

def classify_backlog(queue_depth: int, oldest_age_seconds: int, worker_healthy: bool, at_maximum: bool, resource_headroom: bool) -> dict[str, object]:
    overloaded = queue_depth > 0 and oldest_age_seconds >= 30
    if overloaded and worker_healthy and not at_maximum and resource_headroom:
        return {"outcome": "ACTION_PROPOSED", "action_key": "worker.set_capacity@1"}
    return {"outcome": "ESCALATED", "reason": "worker unhealthy, at capacity, or without headroom"}
