from __future__ import annotations
from jsonschema import Draft202012Validator

def validate_agent_output(payload: dict[str, object], schema: dict[str, object]) -> dict[str, object]:
    Draft202012Validator(schema).validate(payload)
    return payload
