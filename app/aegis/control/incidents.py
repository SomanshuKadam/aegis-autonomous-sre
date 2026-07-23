from __future__ import annotations
from datetime import datetime, timezone
from aegis.control.models import IncidentState
from aegis.control.state_machine import transition
from aegis.types import new_id

class IncidentStore:
    def __init__(self) -> None: self.items: dict[str, dict[str, object]] = {}
    def create(self, category: str, dedup_key: str) -> dict[str, object]:
        existing = next((item for item in self.items.values() if item["dedup_key"] == dedup_key), None)
        if existing: return existing
        incident = {"incident_id": new_id(), "category": category, "dedup_key": dedup_key, "state": IncidentState.DETECTED.value, "timeline": [], "created_at": datetime.now(timezone.utc)}
        self.items[str(incident["incident_id"])] = incident; return incident
    def advance(self, incident_id: str, target: str) -> dict[str, object]:
        incident = self.items[incident_id]; incident["state"] = transition(IncidentState(str(incident["state"])), IncidentState(target)).value
        incident["timeline"].append({"state": incident["state"], "at": datetime.now(timezone.utc)})
        return incident
