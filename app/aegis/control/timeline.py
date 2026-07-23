from __future__ import annotations
from aegis.types import new_id, utc_now
from .models import TimelineEvent
def event(incident_id: str, sequence: int, stage: str, event_type: str, outcome: str, summary: str) -> TimelineEvent:
    return TimelineEvent(event_id=new_id(), incident_id=incident_id, sequence=sequence, occurred_at=utc_now(), stage=stage, type=event_type, outcome=outcome, summary=summary)
