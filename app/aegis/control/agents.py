from __future__ import annotations
from aegis.control.budgets import InvestigationBudget

def evaluate_hypotheses(evidence: list[dict[str, object]], budget: InvestigationBudget) -> dict[str, object]:
    budget.consume_invocation()
    supporting = [entry for entry in evidence if entry.get("fresh") and entry.get("observation")]
    if not supporting: return {"outcome": "INSUFFICIENT_EVIDENCE", "hypotheses": []}
    return {"outcome": "ROOT_CAUSE_IDENTIFIED", "hypotheses": [{"statement": "Observed evidence supports the reported degradation", "evidence_count": len(supporting)}]}
