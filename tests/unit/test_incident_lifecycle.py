from aegis.control.lifecycle import IncidentLifecycle
from aegis.control.timeline import event

def test_lifecycle_progresses_one_guarded_stage_at_a_time() -> None:
    incident = {"incident_id": "incident-1", "state": "DETECTED", "timeline_sequence": 0}
    progressed = IncidentLifecycle().progress(incident)
    assert progressed["state"] == "VALIDATING" and progressed["timeline_sequence"] == 1

def test_timeline_events_keep_technical_and_notification_types_distinct() -> None:
    technical = event("incident-1", 1, "VALIDATING", "technical", "advanced", "validated")
    notification = event("incident-1", 2, "NOTIFYING", "notification", "delivered", "slack delivered")
    assert technical.type == "technical" and notification.type == "notification"
