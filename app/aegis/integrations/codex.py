from __future__ import annotations
from jsonschema import Draft202012Validator
from pathlib import Path

def validate_agent_output(payload: dict[str, object], schema: dict[str, object]) -> dict[str, object]:
    Draft202012Validator(schema).validate(payload)
    return payload

def validate_named_output(payload: dict[str, object], name: str, schema_root: str = "codex/schemas") -> dict[str, object]:
    import json
    path = Path(schema_root) / f"{name}.schema.json"
    if not path.exists(): raise ValueError("agent schema is unavailable")
    return validate_agent_output(payload, json.loads(path.read_text(encoding="utf-8")))
