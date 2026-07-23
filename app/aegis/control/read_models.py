from __future__ import annotations

def incident_summary(incident: dict[str, object]) -> dict[str, object]:
    return {key: incident.get(key) for key in ("incident_id", "category", "state", "created_at", "updated_at", "timeline")}

def overview(incidents: list[dict[str, object]], services: dict[str, object] | None = None) -> dict[str, object]:
    active = [item for item in incidents if item.get("state") not in {"RESOLVED", "FAILED", "ESCALATED", "ROLLED_BACK", "BLOCKED"}]
    latest = incidents[:10]
    return {"status": "ok", "active_incidents": len(active), "incident_count": len(incidents), "services": services or {}, "recent_incidents": [incident_summary(item) for item in latest]}
