from aegis.control.notifications import NotificationRecorder

def test_notification_delivery_is_separate_from_technical_outcome() -> None:
    record = NotificationRecorder().record("incident-1", "slack", False)
    assert record["state"] == "FAILED"
