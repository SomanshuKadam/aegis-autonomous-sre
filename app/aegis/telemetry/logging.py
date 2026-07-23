from __future__ import annotations
SENSITIVE = ("authorization", "token", "secret", "password", "webhook", "prompt")
def redact(values: dict[str, object]) -> dict[str, object]:
    return {key: "[REDACTED]" if any(part in key.lower() for part in SENSITIVE) else redact(value) if isinstance(value, dict) else value for key, value in values.items()}
