from __future__ import annotations
import json
from pathlib import Path
from pydantic import BaseModel, Field

class EvaluationFixture(BaseModel):
    version: int = Field(default=1, ge=1)
    fixture_id: str = Field(min_length=1)
    category: str
    evidence_types: list[str] = []
    action_key: str | None = None
    risk_score: int = 0
    refusal_reason: str | None = None
    expected_outcome: str = "BLOCKED"
    mutation_allowed: bool = False

def load_fixture(path: Path) -> EvaluationFixture:
    payload = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(payload).lower()
    if any(marker in serialized for marker in ("authorization", "password", "secret", "webhook", "token")): raise ValueError("fixture contains forbidden sensitive material")
    return EvaluationFixture.model_validate(payload)
