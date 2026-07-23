from __future__ import annotations
from aegis.control.action_registry import resolve
from aegis.control.fixtures import EvaluationFixture
from aegis.control.policy import evaluate

def evaluate_fixture(fixture: EvaluationFixture) -> dict[str, object]:
    outcome = "BLOCKED"
    reason = "no registered action"
    if fixture.action_key:
        try: outcome = str(evaluate(resolve(fixture.action_key), set(fixture.evidence_types), fixture.risk_score)["outcome"]); reason = "policy evaluated"
        except ValueError as error: reason = str(error)
    return {"fixture_id": fixture.fixture_id, "category": fixture.category, "outcome": outcome, "reason": reason, "live_mutations": 0, "external_notifications": 0}
