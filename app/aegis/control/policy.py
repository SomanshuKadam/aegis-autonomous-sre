from __future__ import annotations
from aegis.control.action_registry import ActionDefinition

def evaluate(action: ActionDefinition, evidence_types: set[str], risk_score: int) -> dict[str, object]:
    if not set(action.required_evidence).issubset(evidence_types): return {"outcome": "BLOCKED", "reason": "required evidence is missing"}
    if action.risk == "LOW" and risk_score <= 2: return {"outcome": "AUTO_APPROVED", "reason": "low risk and complete evidence"}
    if action.risk == "MEDIUM" and risk_score <= 7: return {"outcome": "APPROVAL_REQUIRED", "reason": "operator approval required"}
    return {"outcome": "PROHIBITED", "reason": "risk exceeds policy"}
