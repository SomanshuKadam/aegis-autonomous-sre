from __future__ import annotations
import json
import logging

SENSITIVE = ("authorization", "token", "secret", "password", "webhook", "prompt")
ALLOWED_FIELDS = {"service", "stage", "outcome", "category", "incident_id", "trace_id", "message"}

def redact(values: dict[str, object]) -> dict[str, object]:
    return {key: "[REDACTED]" if any(part in key.lower() for part in SENSITIVE) else redact(value) if isinstance(value, dict) else value for key, value in values.items()}

def structured(logger: logging.Logger, **values: object) -> None:
    safe = redact({key: value for key, value in values.items() if key in ALLOWED_FIELDS})
    logger.info(json.dumps(safe, sort_keys=True, default=str))
