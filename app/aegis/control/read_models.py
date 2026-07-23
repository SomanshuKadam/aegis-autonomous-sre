from __future__ import annotations

def incident_summary(incident: dict[str, object]) -> dict[str, object]:
    return {key: incident.get(key) for key in ("incident_id", "category", "state", "created_at", "updated_at", "timeline")}

def overview(incidents: list[dict[str, object]]) -> dict[str, object]:
    active = [item for item in incidents if item.get("state") not in {"RESOLVED", "FAILED", "ESCALATED", "ROLLED_BACK", "BLOCKED"}]
    return {"status": "ok", "active_incidents": len(active), "incident_count": len(incidents), "health": "unknown", "workload": "unknown", "queue": "unknown", "recent_actions": 0}
