import json
from pathlib import Path
import pytest
from aegis.integrations.codex import validate_agent_output

def test_triage_schema_rejects_incomplete_output() -> None:
    schema = json.loads((Path("/app/codex/schemas/triage-output.schema.json") if Path("/app/codex/schemas/triage-output.schema.json").exists() else Path("codex/schemas/triage-output.schema.json")).read_text())
    assert validate_agent_output({"classification": "catalog", "confidence": 0.9}, schema)["classification"] == "catalog"
    with pytest.raises(Exception): validate_agent_output({"classification": "catalog"}, schema)

@pytest.mark.parametrize(("name", "payload"), [
    ("evidence-output", {"evidence": ["fresh trace"]}),
    ("root-cause-output", {"root_cause": "missing index", "evidence_ids": ["e-1"]}),
    ("remediation-plan-output", {"action_key": "mongo.create_search_index@1", "target": {}}),
    ("verification-output", {"outcome": "VERIFIED", "checks": {}}),
])
def test_agent_role_schemas_accept_only_structured_outputs(name, payload) -> None:
    root = Path("/app/codex/schemas") if Path("/app/codex/schemas").exists() else Path("codex/schemas")
    schema = json.loads((root / f"{name}.schema.json").read_text())
    assert validate_agent_output(payload, schema) == payload
