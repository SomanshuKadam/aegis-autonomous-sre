from __future__ import annotations
from aegis.types import new_id, utc_now

from aegis.control.incidents import IncidentStore

class NotificationRecorder:
    def __init__(self, incidents: IncidentStore) -> None:
        self.incidents = incidents

    def record(self, incident_id: str, channel: str, delivered: bool, detail: str = "") -> dict[str, object]:
        return self.incidents.record("notifications", incident_id, {"notification_id": new_id(), "channel": channel, "state": "DELIVERED" if delivered else "FAILED", "detail": detail, "occurred_at": utc_now()})
