from __future__ import annotations
from aegis.control.action_registry import resolve
from aegis.control.fixtures import EvaluationFixture
from aegis.control.policy import evaluate
from aegis.control.budgets import InvestigationBudget
from aegis.control.agents import triage

def evaluate_fixture(fixture: EvaluationFixture) -> dict[str, object]:
    outcome = "BLOCKED"
    reason = "no registered action"
    triage_outcome = triage(fixture.category, InvestigationBudget(remaining_invocations=1))
    if fixture.action_key and triage_outcome.get("allowed_actions") == fixture.action_key:
        try: outcome = str(evaluate(resolve(fixture.action_key), set(fixture.evidence_types), fixture.risk_score)["outcome"]); reason = "policy evaluated"
        except ValueError as error: reason = str(error)
    return {"fixture_id": fixture.fixture_id, "version": fixture.version, "category": fixture.category, "triage": triage_outcome["outcome"], "outcome": outcome, "reason": reason, "live_mutations": 0, "external_notifications": 0}
