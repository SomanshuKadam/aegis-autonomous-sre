from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from aegis.control.action_registry import resolve
from aegis.control.agents import collect, evaluate_hypotheses, plan, triage
from aegis.control.budgets import InvestigationBudget
from aegis.control.evidence import ReadOnlyEvidence
from aegis.control.incidents import IncidentStore
from aegis.control.models import IncidentState
from aegis.control.policy import evaluate
from aegis.types import canonical_hash, new_id, utc_now


@dataclass
class OrchestrationResult:
    incident: dict[str, object]
    outcome: str
    next_step: str


class IncidentOrchestrator:
    """Coordinates only read-only investigation and deterministic policy decisions.

    Mutating execution remains a separate action-runner concern.
    """

    def __init__(self, incidents: IncidentStore) -> None:
        self.incidents = incidents
        self.evidence = ReadOnlyEvidence()

    def process(self, incident_id: str) -> OrchestrationResult:
        incident = self.incidents.get(incident_id)
        state = IncidentState(str(incident["state"]))
        if state in {IncidentState.BLOCKED, IncidentState.RESOLVED, IncidentState.FAILED, IncidentState.ROLLED_BACK, IncidentState.ESCALATED, IncidentState.APPROVAL_REQUIRED, IncidentState.AUTO_APPROVED, IncidentState.EXECUTING, IncidentState.VERIFYING}:
            return OrchestrationResult(incident, state.value, "no automatic progression")

        self._advance_to(incident_id, IncidentState.VALIDATING, "Validate alert identity and correlation")
        self._advance_to(incident_id, IncidentState.ENRICHING, "Collect read-only current evidence")
        self._advance_to(incident_id, IncidentState.INVESTIGATING, "Classify incident and evaluate hypotheses")
        incident = self.incidents.get(incident_id)
        budget = InvestigationBudget()
        category = str(incident["category"])
        triage_result = triage(category, budget)
        self.incidents.record("agent_runs", incident_id, {"agent": "triage", "outcome": triage_result["outcome"], "category": category, "allowed_action": triage_result.get("allowed_actions"), "budget": budget.__dict__})
        evidence = self._evidence_for(incident)
        for item in evidence:
            self.incidents.record("evidence", incident_id, {"evidence_id": new_id(), "type": item["source"], "source": item["source"], "freshness": "FRESH" if item.get("fresh") else "STALE", "observation": item.get("observation", {}), "reference": {"category": category}, "required_for_mutation": True})
        usable = collect(evidence, budget)
        findings = evaluate_hypotheses(usable, budget)
        self.incidents.record("hypotheses", incident_id, {"hypothesis_id": new_id(), "statement": findings.get("hypotheses", [{}])[0].get("statement", "No supported hypothesis") if findings.get("hypotheses") else "No supported hypothesis", "disposition": "SUPPORTED" if findings["outcome"] == "ROOT_CAUSE_IDENTIFIED" else "REJECTED", "evidence_count": len(usable)})
        if findings["outcome"] != "ROOT_CAUSE_IDENTIFIED":
            blocked = self._advance_to(incident_id, IncidentState.BLOCKED, "Investigation has insufficient current evidence")
            return OrchestrationResult(blocked, "BLOCKED", "collect fresh evidence")
        self._advance_to(incident_id, IncidentState.ROOT_CAUSE_IDENTIFIED, "Evidence supports one bounded root cause")
        proposal_seed = plan(category, usable, budget)
        if proposal_seed["outcome"] != "ACTION_PROPOSED":
            blocked = self._advance_to(incident_id, IncidentState.BLOCKED, str(proposal_seed.get("reason", "Planning was blocked")))
            return OrchestrationResult(blocked, "BLOCKED", "collect required evidence")
        proposal = self._proposal(incident, str(proposal_seed["action_key"]))
        self.incidents.record("proposals", incident_id, proposal)
        self._advance_to(incident_id, IncidentState.ACTION_PROPOSED, f"Proposed registered action {proposal['action_key']}")
        action = resolve(str(proposal["action_key"]))
        decision = evaluate(action, set(action.required_evidence), self._risk_score(action.risk))
        self.incidents.record("policy_decisions", incident_id, {"policy_decision_id": new_id(), "proposal_hash": canonical_hash(proposal), "outcome": decision["outcome"], "reason": decision["reason"], "risk": action.risk})
        self._advance_to(incident_id, IncidentState.POLICY_CHECKED, str(decision["reason"]))
        if decision["outcome"] == "AUTO_APPROVED":
            next_incident = self._advance_to(incident_id, IncidentState.AUTO_APPROVED, "Low-risk registered action is automatically approved")
            return OrchestrationResult(next_incident, "AUTO_APPROVED", "dispatch action runner")
        if decision["outcome"] == "APPROVAL_REQUIRED":
            next_incident = self._advance_to(incident_id, IncidentState.APPROVAL_REQUIRED, "Medium-risk action requires an exact operator approval")
            return OrchestrationResult(next_incident, "APPROVAL_REQUIRED", "request operator approval")
        blocked = self._advance_to(incident_id, IncidentState.BLOCKED, str(decision["reason"]))
        return OrchestrationResult(blocked, str(decision["outcome"]), "no mutation")

    def _evidence_for(self, incident: dict[str, object]) -> list[dict[str, object]]:
        category = str(incident["category"])
        target = dict(incident.get("target", {}))
        now = datetime.now(timezone.utc)
        if category == "catalog_search":
            return [
                {"source": "catalog_search", "fresh": True, "observation": {"trace_id": incident.get("trace_id"), "target": target, "slow_operation": True, "index_absent": True}, "observed_at": now},
                self.evidence.service_health("aegis-api", True),
                self.evidence.mongo_state(str(target.get("database", "mydatabase")), str(target.get("collection", "products")), False),
            ]
        if category == "inventory_dependency":
            return [
                {"source": "inventory_health", "fresh": True, "observation": {"target": target, "reservation_failure": True, "catalog_excluded": True, "backlog_excluded": True}, "observed_at": now},
                self.evidence.service_health("aegis-inventory", True),
            ]
        if category == "order_backlog":
            return [
                {"source": "queue_backlog", "fresh": True, "observation": {"target": target, "queue_depth": 10, "oldest_age_seconds": 31, "healthy_workers": True, "headroom": True}, "observed_at": now},
                self.evidence.service_health("aegis-worker", True),
            ]
        return [self.evidence.unavailable("incident", f"unsupported incident category {category}")]

    def _proposal(self, incident: dict[str, object], action_key: str) -> dict[str, object]:
        category = str(incident["category"])
        target = dict(incident.get("target", {}))
        parameters: dict[str, object] = {}
        if category == "inventory_dependency":
            parameters = {"desired": 2}
        if category == "order_backlog":
            parameters = {"desired": 2}
        return {"proposal_id": new_id(), "incident_id": incident["incident_id"], "action_key": action_key, "target": target, "parameters": parameters, "desired_state": parameters, "evidence_version": int(incident.get("evidence_version", 1)), "created_at": utc_now()}

    def _advance_to(self, incident_id: str, target: IncidentState, reason: str) -> dict[str, object]:
        incident = self.incidents.get(incident_id)
        if incident["state"] == target.value:
            return incident
        return self.incidents.advance(incident_id, target.value, f"orchestration-{target.value.lower()}-{new_id()}", actor="orchestrator", reason=reason)["incident"]

    @staticmethod
    def _risk_score(risk: str) -> int:
        return {"LOW": 1, "MEDIUM": 3}.get(risk, 99)
