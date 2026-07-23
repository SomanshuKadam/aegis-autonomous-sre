from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from fastapi.encoders import jsonable_encoder
from pymongo import MongoClient

from aegis.control.action_registry import resolve
from aegis.control.approvals import ApprovalStore
from aegis.control.agents import collect, evaluate_hypotheses, plan, triage
from aegis.control.budgets import InvestigationBudget
from aegis.control.evidence import ReadOnlyEvidence
from aegis.control.incidents import IncidentStore
from aegis.control.models import IncidentState
from aegis.control.policy import evaluate
from aegis.control.verification import verify_profile
from aegis.config import Settings, get_settings
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

    def __init__(self, incidents: IncidentStore, settings: Settings | None = None) -> None:
        self.incidents = incidents
        self.settings = settings or get_settings()
        self.evidence = ReadOnlyEvidence()
        self.db = MongoClient(self.settings.mongodb_uri.get_secret_value(), serverSelectionTimeoutMS=5000)[self.settings.mongo_database]
        self.approvals = ApprovalStore(incidents)

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
            self._advance_to(incident_id, IncidentState.AUTO_APPROVED, "Low-risk registered action is automatically approved")
            return self._dispatch_and_verify(incident_id, proposal)
        if decision["outcome"] == "APPROVAL_REQUIRED":
            next_incident = self._advance_to(incident_id, IncidentState.APPROVAL_REQUIRED, "Medium-risk action requires an exact operator approval")
            approval = self.approvals.request(incident_id, proposal)
            return OrchestrationResult(next_incident, "APPROVAL_REQUIRED", f"await approval {approval['approval_id']}")
        blocked = self._advance_to(incident_id, IncidentState.BLOCKED, str(decision["reason"]))
        return OrchestrationResult(blocked, str(decision["outcome"]), "no mutation")

    def approve(self, incident_id: str, approval_id: str, approver: str, decision: str) -> OrchestrationResult:
        incident = self.incidents.get(incident_id)
        if incident["state"] != IncidentState.APPROVAL_REQUIRED.value:
            return OrchestrationResult(incident, str(incident["state"]), "approval is not applicable")
        proposals = self.incidents.records(incident_id)["proposals"]
        if not proposals:
            raise ValueError("approval has no proposal")
        proposal = proposals[-1]
        approval = self.approvals.consume(incident_id, approval_id, proposal, approver, decision)
        if approval["state"] == "REJECTED":
            blocked = self._advance_to(incident_id, IncidentState.BLOCKED, "Operator rejected the exact pending proposal")
            return OrchestrationResult(blocked, "BLOCKED", "no mutation")
        return self._dispatch_and_verify(incident_id, proposal)

    def _evidence_for(self, incident: dict[str, object]) -> list[dict[str, object]]:
        category = str(incident["category"])
        target = dict(incident.get("target", {}))
        now = datetime.now(timezone.utc)
        if category == "catalog_search":
            index_present = "search_text_1" in self.db["products"].index_information()
            return [
                {"source": "catalog_search", "fresh": True, "observation": {"trace_id": incident.get("trace_id"), "target": target, "slow_operation": not index_present, "index_absent": not index_present}, "observed_at": now},
                self.evidence.service_health("aegis-api", True),
                self.evidence.mongo_state(str(target.get("database", "mydatabase")), str(target.get("collection", "products")), index_present),
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

    def _dispatch_and_verify(self, incident_id: str, proposal: dict[str, object]) -> OrchestrationResult:
        self._advance_to(incident_id, IncidentState.EXECUTING, "Dispatch approved action to the isolated runner")
        execution_id = new_id()
        try:
            response = httpx.post(
                f"{self.settings.runner_url.rstrip('/')}/actions/execute",
                headers={"Authorization": f"Bearer {self.settings.runner_token.get_secret_value()}"},
                json={"proposal": jsonable_encoder(proposal)},
                timeout=65,
            )
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as exc:
            self.incidents.record("executions", incident_id, {"execution_id": execution_id, "idempotency_key": execution_id, "proposal_id": proposal["proposal_id"], "state": "FAILED", "attempt_number": 1, "error": str(exc)})
            failed = self._advance_to(incident_id, IncidentState.FAILED, "Action runner did not complete the approved action")
            return OrchestrationResult(failed, "FAILED", "inspect runner execution")
        self.incidents.record("executions", incident_id, {"execution_id": execution_id, "idempotency_key": execution_id, "proposal_id": proposal["proposal_id"], "state": str(result.get("state", "SUCCEEDED")), "attempt_number": 1, "runner_result": result})
        self._advance_to(incident_id, IncidentState.VERIFYING, "Verify the intended state and a fresh business result")
        observed = self._verification_observation(proposal)
        expected = self._verification_expectation(proposal)
        verification = verify_profile(str(resolve(str(proposal["action_key"])).verification_profile), expected, observed, bool(observed.get("business_result")), True)
        self.incidents.record("verifications", incident_id, {"verification_id": new_id(), "execution_id": execution_id, **verification, "observed": observed})
        if verification["outcome"] == "VERIFIED":
            resolved = self._advance_to(incident_id, IncidentState.RESOLVED, "Runner mutation and fresh catalog query were verified")
            return OrchestrationResult(resolved, "RESOLVED", "notify operations")
        failed = self._advance_to(incident_id, IncidentState.FAILED, "Runner mutation could not be verified")
        return OrchestrationResult(failed, "FAILED", "inspect verification evidence")

    def _verification_observation(self, proposal: dict[str, object]) -> dict[str, object]:
        if proposal["action_key"] == "mongo.create_search_index@1":
            products = self.db["products"]
            return {"index_present": "search_text_1" in products.index_information(), "business_result": products.find_one({"search_text": "aegis notebook reliability"}) is not None}
        url = self.settings.inventory_url if proposal["action_key"] == "inventory.restore_capacity@1" else self.settings.worker_url
        health = httpx.get(f"{url.rstrip('/')}/health", timeout=10).json()
        desired = int(dict(proposal["parameters"])["desired"])
        business_result = bool(health.get("status") == "ok" and health.get("capacity") == desired)
        return {"capacity": health.get("capacity"), "business_result": business_result}

    @staticmethod
    def _verification_expectation(proposal: dict[str, object]) -> dict[str, object]:
        if proposal["action_key"] == "mongo.create_search_index@1":
            return {"index_present": True, "business_result": True}
        return {"capacity": int(dict(proposal["parameters"])["desired"]), "business_result": True}

    def _advance_to(self, incident_id: str, target: IncidentState, reason: str) -> dict[str, object]:
        incident = self.incidents.get(incident_id)
        if incident["state"] == target.value:
            return incident
        return self.incidents.advance(incident_id, target.value, f"orchestration-{target.value.lower()}-{new_id()}", actor="orchestrator", reason=reason)["incident"]

    @staticmethod
    def _risk_score(risk: str) -> int:
        return {"LOW": 1, "MEDIUM": 3}.get(risk, 99)
