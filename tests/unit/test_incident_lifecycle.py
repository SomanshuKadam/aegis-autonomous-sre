from aegis.control.lifecycle import IncidentLifecycle

def test_lifecycle_progresses_one_guarded_stage_at_a_time() -> None:
    incident = {"incident_id": "incident-1", "state": "DETECTED", "timeline_sequence": 0}
    progressed = IncidentLifecycle().progress(incident)
    assert progressed["state"] == "VALIDATING" and progressed["timeline_sequence"] == 1
