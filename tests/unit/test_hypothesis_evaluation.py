from datetime import datetime, timezone
from aegis.control.agents import evaluate_hypotheses
from aegis.control.budgets import InvestigationBudget
from aegis.control.evidence import fresh

def test_fresh_evidence_selects_bounded_hypothesis() -> None:
    result = evaluate_hypotheses([fresh("health", {"status": "degraded"}, datetime.now(timezone.utc))], InvestigationBudget())
    assert result["outcome"] == "ROOT_CAUSE_IDENTIFIED"
