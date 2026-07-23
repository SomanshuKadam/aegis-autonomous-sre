from __future__ import annotations
from aegis.control.budgets import InvestigationBudget

def triage(category: str, budget: InvestigationBudget) -> dict[str, object]:
    budget.consume_invocation()
    return {"category": category, "outcome": "TRIAGED", "allowed_actions": {"catalog_search": "mongo.create_search_index@1", "inventory_dependency": "inventory.restore_capacity@1", "order_backlog": "worker.set_capacity@1"}.get(category)}

def collect(evidence: list[dict[str, object]], budget: InvestigationBudget) -> list[dict[str, object]]:
    budget.consume_tool_call()
    return [entry for entry in evidence if entry.get("fresh") and not entry.get("unavailable")]

def evaluate_hypotheses(evidence: list[dict[str, object]], budget: InvestigationBudget) -> dict[str, object]:
    budget.consume_invocation()
    supporting = [entry for entry in evidence if entry.get("fresh") and entry.get("observation")]
    if not supporting: return {"outcome": "INSUFFICIENT_EVIDENCE", "hypotheses": []}
    budget.consume_hypothesis()
    return {"outcome": "ROOT_CAUSE_IDENTIFIED", "hypotheses": [{"statement": "Observed evidence supports the reported degradation", "evidence_count": len(supporting), "disposition": "SUPPORTED"}]}

def plan(category: str, evidence: list[dict[str, object]], budget: InvestigationBudget) -> dict[str, object]:
    decision = triage(category, budget)
    if not decision["allowed_actions"] or not collect(evidence, budget):
        return {"outcome": "BLOCKED", "reason": "required fresh evidence is missing"}
    return {"outcome": "ACTION_PROPOSED", "action_key": decision["allowed_actions"]}
