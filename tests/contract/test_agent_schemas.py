import json
from pathlib import Path
import pytest
from aegis.integrations.codex import validate_agent_output

def test_triage_schema_rejects_incomplete_output() -> None:
    schema = json.loads((Path("/app/codex/schemas/triage-output.schema.json") if Path("/app/codex/schemas/triage-output.schema.json").exists() else Path("codex/schemas/triage-output.schema.json")).read_text())
    assert validate_agent_output({"classification": "catalog", "confidence": 0.9}, schema)["classification"] == "catalog"
    with pytest.raises(Exception): validate_agent_output({"classification": "catalog"}, schema)
