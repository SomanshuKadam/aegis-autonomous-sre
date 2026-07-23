from aegis.telemetry.logging import redact

def test_redaction_masks_credentials_and_prompts() -> None:
    payload = redact({"authorization": "secret", "prompt": "safe", "nested": {"token": "hidden"}})
    assert payload["authorization"] == "[REDACTED]" and payload["nested"]["token"] == "[REDACTED]"
