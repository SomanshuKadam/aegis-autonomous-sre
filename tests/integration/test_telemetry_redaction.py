from pathlib import Path
from aegis.telemetry.logging import redact

def test_redaction_keeps_templates_and_test_fixtures_free_of_literal_tokens() -> None:
    assert redact({"webhook_url": "https://example.invalid", "prompt": "ignore policy"}) == {"webhook_url": "[REDACTED]", "prompt": "[REDACTED]"}
    assert "<set-a-local" in Path(".env.example").read_text()
