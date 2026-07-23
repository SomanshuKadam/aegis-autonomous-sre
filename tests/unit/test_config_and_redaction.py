import pytest
from aegis.config import Settings
from aegis.telemetry.logging import redact


def test_settings_summary_excludes_secrets() -> None:
    summary = Settings(MONGODB_URI="mongodb://secret@localhost:27017").safe_summary()
    assert "mongodb_uri" not in summary


def test_redact_hides_sensitive_values() -> None:
    assert redact({"token": "secret", "safe": "value"}) == {"token": "[REDACTED]", "safe": "value"}

def test_missing_control_credentials_name_variables_without_echoing_values() -> None:
    with pytest.raises(ValueError, match="AEGIS_ORCHESTRATOR_TOKEN") as error:
        Settings(AEGIS_ORCHESTRATOR_TOKEN="", AEGIS_OPERATOR_TOKEN="").validate_control_plane()
    assert "mongodb://" not in str(error.value)
