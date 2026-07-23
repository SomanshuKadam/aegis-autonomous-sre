from __future__ import annotations
from aegis.types import new_id, utc_now

class NotificationRecorder:
    def __init__(self) -> None: self.records: list[dict[str, object]] = []
    def record(self, incident_id: str, channel: str, delivered: bool) -> dict[str, object]:
        record = {"notification_id": new_id(), "incident_id": incident_id, "channel": channel, "state": "DELIVERED" if delivered else "FAILED", "occurred_at": utc_now()}
        self.records.append(record); return record
