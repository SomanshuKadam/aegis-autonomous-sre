from aegis.config import Settings
from aegis.telemetry.logging import redact


def test_settings_summary_excludes_secrets() -> None:
    summary = Settings(MONGODB_URI="mongodb://secret@localhost:27017").safe_summary()
    assert "mongodb_uri" not in summary


def test_redact_hides_sensitive_values() -> None:
    assert redact({"token": "secret", "safe": "value"}) == {"token": "[REDACTED]", "safe": "value"}
