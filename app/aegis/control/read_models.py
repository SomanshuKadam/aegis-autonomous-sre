from __future__ import annotations

def incident_summary(incident: dict[str, object]) -> dict[str, object]:
    return {key: incident.get(key) for key in ("incident_id", "category", "state", "created_at", "updated_at", "timeline")}

def overview(incidents: list[dict[str, object]], services: dict[str, object] | None = None, *, active_incidents: int | None = None, incident_count: int | None = None) -> dict[str, object]:
    active = [item for item in incidents if item.get("state") not in {"RESOLVED", "FAILED", "ESCALATED", "ROLLED_BACK", "BLOCKED"}]
    latest = incidents[:10]
    return {"status": "ok", "active_incidents": len(active) if active_incidents is None else active_incidents, "incident_count": len(incidents) if incident_count is None else incident_count, "services": services or {}, "recent_incidents": [incident_summary(item) for item in latest]}
