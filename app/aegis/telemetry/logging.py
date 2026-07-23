from __future__ import annotations
SENSITIVE = ("authorization", "token", "secret", "password", "webhook")
def redact(values: dict[str, object]) -> dict[str, object]: return {key: "[REDACTED]" if any(part in key.lower() for part in SENSITIVE) else value for key, value in values.items()}
