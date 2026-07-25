from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging

import httpx
import time
from fastapi.encoders import jsonable_encoder
from pymongo import MongoClient
from opentelemetry import trace

from aegis.control.action_registry import resolve
from aegis.control.approvals import ApprovalStore
from aegis.control.backlog_incident import classify_backlog
from aegis.control.evidence import ReadOnlyEvidence
from aegis.control.incidents import IncidentStore
from aegis.control.models import IncidentState
from aegis.control.state_machine import TERMINAL
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
    """Owns the durable incident lifecycle while the runner owns bounded mutation."""

    def __init__(self, incidents: IncidentStore, settings: Settings | None = None) -> None:
        self.incidents = incidents
        self.settings = settings or get_settings()
        self.evidence = ReadOnlyEvidence()
        self.db = MongoClient(self.settings.mongodb_uri.get_secret_value(), serverSelectionTimeoutMS=5000)[self.settings.mongo_database]
        self.approvals = ApprovalStore(incidents)
        self.tracer = trace.get_tracer("aegis.orchestration")
        self.logger = logging.getLogger("aegis.orchestration")

    def process(self, incident_id: str) -> OrchestrationResult:
        incident = self.incidents.get(incident_id)
        with self.tracer.start_as_current_span("incident.process") as span:
            span.set_attribute("aegis.incident_id", incident_id)
            span.set_attribute("aegis.incident.category", str(incident["category"]))
            return self._record_terminal_notification(self._process(incident_id, incident))

    def _process(self, incident_id: str, incident: dict[str, object]) -> OrchestrationResult:
        state = IncidentState(str(incident["state"]))
        if state in {IncidentState.BLOCKED, IncidentState.RESOLVED, IncidentState.FAILED, IncidentState.ROLLED_BACK, IncidentState.ESCALATED, IncidentState.APPROVAL_REQUIRED, IncidentState.AUTO_APPROVED, IncidentState.EXECUTING, IncidentState.VERIFYING}:
            return OrchestrationResult(incident, state.value, "no automatic progression")

        self._advance_to(incident_id, IncidentState.VALIDATING, "Validate alert identity and correlation")
        self._advance_to(incident_id, IncidentState.ENRICHING, "Collect read-only current evidence")
        self._advance_to(incident_id, IncidentState.INVESTIGATING, "Validate the recorded Codex SigNoz investigation")
        incident = self.incidents.get(incident_id)
        category = str(incident["category"])
        agent_runs = [
            item
            for item in self.incidents.records(incident_id)["agent_runs"]
            if item.get("agent") == "codex-signoz-investigator"
        ]
        if not agent_runs:
            blocked = self._advance_to(
                incident_id,
                IncidentState.BLOCKED,
                "No validated Codex SigNoz investigation is attached to this incident",
            )
            return OrchestrationResult(blocked, "BLOCKED", "run the read-only Codex investigation")
        agent_result = agent_runs[-1]
        evidence = self._evidence_for(incident)
        for item in evidence:
            self.incidents.record("evidence", incident_id, {"evidence_id": new_id(), "type": item["source"], "source": item["source"], "freshness": "FRESH" if item.get("fresh") else "STALE", "observation": item.get("observation", {}), "reference": {"category": category, "source_trace_id": incident.get("trace_id")}, "required_for_mutation": True})
        self.incidents.record(
            "hypotheses",
            incident_id,
            {
                "hypothesis_id": new_id(),
                "statement": str(agent_result.get("diagnosis", "Codex returned no diagnosis")),
                "plausible_solution": str(agent_result.get("plausible_solution", "")),
                "disposition": "SUPPORTED" if agent_result.get("safe_to_proceed") else "REJECTED",
                "evidence": list(agent_result.get("evidence", [])),
                "source": "codex-signoz-investigator",
            },
        )
        if not agent_result.get("safe_to_proceed"):
            blocked = self._advance_to(
                incident_id,
                IncidentState.BLOCKED,
                "Codex did not find sufficient current SigNoz evidence for a bounded action",
            )
            return OrchestrationResult(blocked, "BLOCKED", "review the Codex diagnosis and telemetry")
        if not self._has_required_condition(category, evidence):
            blocked = self._advance_to(incident_id, IncidentState.BLOCKED, "Required current evidence does not prove the reported bounded condition")
            return OrchestrationResult(blocked, "BLOCKED", "collect current incident evidence")
        if category == "order_backlog":
            observation = dict(evidence[0].get("observation", {}))
            disposition = classify_backlog(int(observation.get("queue_depth", 0)), int(observation.get("oldest_age_seconds", 0)), bool(observation.get("healthy_workers")), bool(observation.get("at_maximum")), bool(observation.get("headroom")))
            if disposition["outcome"] != "ACTION_PROPOSED":
                self.incidents.record("policy_decisions", incident_id, {"policy_decision_id": new_id(), "outcome": "ESCALATED", "reason": disposition["reason"], "risk": "LOW"})
                escalated = self._advance_to(incident_id, IncidentState.ESCALATED, str(disposition["reason"]))
                return OrchestrationResult(escalated, "ESCALATED", "no mutation")
        self._advance_to(incident_id, IncidentState.ROOT_CAUSE_IDENTIFIED, "Evidence supports one bounded root cause")
        action_key = str(agent_result.get("selected_action", "none"))
        expected_action = {
            "catalog_search": "mongo.create_search_index@1",
            "inventory_dependency": "inventory.restore_capacity@1",
            "order_backlog": "worker.set_capacity@1",
        }.get(category)
        if action_key != expected_action:
            blocked = self._advance_to(incident_id, IncidentState.BLOCKED, "Codex action selection does not match the registered action for this incident")
            return OrchestrationResult(blocked, "BLOCKED", "no mutation")
        proposal = self._proposal(incident, action_key)
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
        with self.tracer.start_as_current_span("incident.approval") as span:
            span.set_attribute("aegis.incident_id", incident_id)
            span.set_attribute("aegis.approval.decision", decision)
            return self._record_terminal_notification(self._approve(incident_id, incident, approval_id, approver, decision))

    def reconcile_expired_approvals(self) -> list[dict[str, str]]:
        return self.approvals.reconcile_expired()

    def reopen_approval(
        self,
        incident_id: str,
        expired_approval_id: str,
        approver: str,
    ) -> OrchestrationResult:
        incident = self.incidents.get(incident_id)
        if (
            incident["state"] != IncidentState.ESCALATED.value
            or incident.get("escalation_reason") != "approval_expired"
            or incident.get("expired_approval_id") != expired_approval_id
        ):
            raise ValueError("incident is not eligible for approval reopening")
        proposals = self.incidents.records(incident_id)["proposals"]
        if not proposals:
            raise ValueError("approval reopening requires the original proposal")
        approval = self.approvals.reopen(incident_id, expired_approval_id, proposals[-1])
        try:
            reopened = self.incidents.reopen_expired_approval(
                incident_id,
                expired_approval_id,
                utc_now(),
            )
        except ValueError:
            self.approvals.cancel(
                str(approval["approval_id"]),
                "Approval attempt cancelled because the incident could not be reopened",
            )
            raise
        reopened["approval"] = approval
        reopened["reopened_by"] = approver
        return OrchestrationResult(
            reopened,
            IncidentState.APPROVAL_REQUIRED.value,
            f"await approval {approval['approval_id']}",
        )

    def _record_terminal_notification(self, result: OrchestrationResult) -> OrchestrationResult:
        state = IncidentState(str(result.incident["state"]))
        if state not in TERMINAL:
            return result
        existing = self.incidents.db["notifications"].find_one(
            {"incident_id": result.incident["incident_id"], "channel": "console", "terminal_state": state.value}
        )
        if existing is None:
            self.incidents.record(
                "notifications",
                str(result.incident["incident_id"]),
                {
                    "notification_id": new_id(),
                    "channel": "console",
                    "terminal_state": state.value,
                    "state": "DELIVERED",
                    "detail": f"terminal incident state {state.value} recorded for operations console",
                },
            )
        return result

    def _approve(self, incident_id: str, incident: dict[str, object], approval_id: str, approver: str, decision: str) -> OrchestrationResult:
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
            trace_id = str(incident.get("trace_id") or "")
            query: dict[str, object] = {"occurred_at": {"$gte": now - timedelta(minutes=5)}}
            if trace_id:
                query["trace_id"] = trace_id
            operations = list(self.db["catalog_operations"].find(query, {"_id": 0}).sort("occurred_at", -1).limit(20))
            latencies = sorted(float(operation.get("latency_ms", 0.0)) for operation in operations)
            p95_latency_ms = latencies[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0.0
            recent_trace_observed = bool(operations) and (not trace_id or str(operations[0].get("trace_id")) == trace_id)
            return [
                {"source": "catalog_search", "fresh": recent_trace_observed, "observation": {"trace_id": trace_id or None, "target": target, "sample_count": len(operations), "p95_latency_ms": p95_latency_ms, "slow_operation": recent_trace_observed and p95_latency_ms >= self.settings.search_recovery_ms, "index_absent": not index_present}, "observed_at": now},
                self.evidence.service_health("aegis-api", True),
                self.evidence.mongo_state(str(target.get("database", "mydatabase")), str(target.get("collection", "products")), index_present),
            ]
        if category == "inventory_dependency":
            health = httpx.get(f"{self.settings.inventory_url.rstrip('/')}/health", timeout=10).json()
            metrics = dict(health.get("metrics", {}))
            worker = httpx.get(f"{self.settings.worker_url.rstrip('/')}/health", timeout=10).json()
            index_present = "search_text_1" in self.db["products"].index_information()
            return [
                {"source": "inventory_health", "fresh": True, "observation": {"target": target, "reservation_failure": int(metrics.get("failures", 0)) > 0, "error_rate": metrics.get("error_rate", 0.0), "p95_latency_ms": metrics.get("p95_latency_ms", 0.0), "capacity": health.get("capacity"), "saturated": health.get("resource_saturated"), "catalog_excluded": index_present, "backlog_excluded": not (int(worker.get("queue_depth", 0)) > 0 and int(worker.get("oldest_age_seconds", 0)) >= 30)}, "observed_at": now},
                self.evidence.service_health("aegis-inventory", health.get("status") == "ok"),
            ]
        if category == "order_backlog":
            health = httpx.get(f"{self.settings.worker_url.rstrip('/')}/health", timeout=10).json()
            capacity = int(health.get("capacity", 0)); maximum = int(health.get("maximum", 4))
            return [
                {"source": "queue_backlog", "fresh": True, "observation": {"target": target, "queue_depth": int(health.get("queue_depth", 0)), "oldest_age_seconds": int(health.get("oldest_age_seconds", 0)), "healthy_workers": health.get("status") == "ok", "headroom": bool(health.get("resource_headroom")), "at_maximum": capacity >= maximum, "capacity": capacity, "maximum": maximum, "worker_failures": int(health.get("failures", 0))}, "observed_at": now},
                self.evidence.service_health("aegis-worker", health.get("status") == "ok"),
            ]
        return [self.evidence.unavailable("incident", f"unsupported incident category {category}")]

    def _proposal(self, incident: dict[str, object], action_key: str) -> dict[str, object]:
        category = str(incident["category"])
        target = dict(incident.get("target", {}))
        parameters: dict[str, object] = {}
        if category == "inventory_dependency":
            health = httpx.get(f"{self.settings.inventory_url.rstrip('/')}/health", timeout=10).json()
            parameters = {"desired": min(int(health.get("capacity", 1)) + 1, int(health.get("maximum", 4)))}
        if category == "order_backlog":
            health = httpx.get(f"{self.settings.worker_url.rstrip('/')}/health", timeout=10).json()
            parameters = {"desired": int(health.get("capacity", 1)) + 1}
        proposal = {"proposal_id": new_id(), "incident_id": incident["incident_id"], "action_key": action_key, "target": target, "parameters": parameters, "desired_state": parameters, "evidence_version": int(incident.get("evidence_version", 1)), "created_at": utc_now()}
        if category == "order_backlog":
            proposal["backlog_baseline"] = {"queue_depth": int(health.get("queue_depth", 0)), "oldest_age_seconds": int(health.get("oldest_age_seconds", 0)), "failures": int(health.get("failures", 0))}
        return proposal

    def _dispatch_and_verify(self, incident_id: str, proposal: dict[str, object]) -> OrchestrationResult:
        with self.tracer.start_as_current_span("incident.execute") as span:
            span.set_attribute("aegis.incident_id", incident_id)
            span.set_attribute("aegis.action", str(proposal["action_key"]))
            return self._dispatch_and_verify_inner(incident_id, proposal)

    def _dispatch_and_verify_inner(self, incident_id: str, proposal: dict[str, object]) -> OrchestrationResult:
        self._advance_to(incident_id, IncidentState.EXECUTING, "Dispatch approved action to the isolated runner")
        execution_id = new_id()
        idempotency_key = canonical_hash({"incident_id": incident_id, "proposal_id": proposal["proposal_id"], "evidence_version": proposal["evidence_version"]})
        runner_proposal = {**proposal, "idempotency_key": idempotency_key}
        try:
            response = httpx.post(
                f"{self.settings.runner_url.rstrip('/')}/actions/execute",
                headers={"Authorization": f"Bearer {self.settings.runner_token.get_secret_value()}"},
                json={"proposal": jsonable_encoder(runner_proposal)},
                timeout=65,
            )
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as exc:
            self.incidents.record("executions", incident_id, {"execution_id": execution_id, "idempotency_key": idempotency_key, "proposal_id": proposal["proposal_id"], "state": "FAILED", "attempt_number": 1, "error": str(exc)})
            return self._rollback_or_escalate(incident_id, execution_id, idempotency_key, proposal, {}, "action runner did not complete the approved action")
        execution = {"execution_id": execution_id, "idempotency_key": idempotency_key, "proposal_id": proposal["proposal_id"], "state": str(result.get("state", "SUCCEEDED")), "attempt_number": 1, "runner_result": result, "previous_state": result.get("previous_state", {})}
        self.incidents.record("executions", incident_id, execution)
        if execution["state"] not in {"SUCCEEDED", "NOOP", "DUPLICATE"}:
            return self._rollback_or_escalate(incident_id, execution_id, idempotency_key, proposal, dict(execution["previous_state"]), "runner reported a non-successful action outcome")
        self._advance_to(incident_id, IncidentState.VERIFYING, "Verify the intended state and a fresh business result")
        observed = self._verification_observation(proposal)
        expected = self._verification_expectation(proposal)
        verification = verify_profile(str(resolve(str(proposal["action_key"])).verification_profile), expected, observed, bool(observed.get("business_result")), True)
        self.incidents.record("verifications", incident_id, {"verification_id": new_id(), "execution_id": execution_id, **verification, "observed": observed})
        if verification["outcome"] == "VERIFIED":
            resolved = self._advance_to(incident_id, IncidentState.RESOLVED, "Registered action and fresh business behavior were verified")
            return OrchestrationResult(resolved, "RESOLVED", "notify operations")
        return self._rollback_or_escalate(incident_id, execution_id, idempotency_key, proposal, dict(execution["previous_state"]), "post-action verification did not satisfy the frozen criteria")

    def _rollback_or_escalate(self, incident_id: str, execution_id: str, idempotency_key: str, proposal: dict[str, object], previous_state: dict[str, object], reason: str) -> OrchestrationResult:
        action = resolve(str(proposal["action_key"]))
        rollback_id = new_id()
        if not action.rollback_action or not previous_state:
            self.incidents.record("rollbacks", incident_id, {"rollback_id": rollback_id, "execution_id": execution_id, "outcome": "ESCALATED", "reason": reason, "attempt_number": 0})
            escalated = self._advance_to(incident_id, IncidentState.ESCALATED, f"{reason}; no safe compensating action is available")
            return OrchestrationResult(escalated, "ESCALATED", "operator investigation required")
        try:
            response = httpx.post(
                f"{self.settings.runner_url.rstrip('/')}/actions/rollback",
                headers={"Authorization": f"Bearer {self.settings.runner_token.get_secret_value()}"},
                json={"action_key": proposal["action_key"], "target": proposal["target"], "previous_state": previous_state, "idempotency_key": idempotency_key},
                timeout=65,
            )
            response.raise_for_status()
            outcome = response.json()
        except httpx.HTTPError as exc:
            self.incidents.record("rollbacks", incident_id, {"rollback_id": rollback_id, "execution_id": execution_id, "outcome": "ESCALATED", "reason": reason, "attempt_number": 1, "error": str(exc)})
            escalated = self._advance_to(incident_id, IncidentState.ESCALATED, f"{reason}; the one allowed rollback failed")
            return OrchestrationResult(escalated, "ESCALATED", "operator investigation required")
        self.incidents.record("rollbacks", incident_id, {"rollback_id": rollback_id, "execution_id": execution_id, "outcome": "ROLLED_BACK", "reason": reason, "attempt_number": 1, "previous_state": previous_state, "runner_result": outcome})
        rolled_back = self._advance_to(incident_id, IncidentState.ROLLED_BACK, f"{reason}; one registered compensation restored the previous state")
        return OrchestrationResult(rolled_back, "ROLLED_BACK", "operator review required")

    def _verification_observation(self, proposal: dict[str, object]) -> dict[str, object]:
        if proposal["action_key"] == "mongo.create_search_index@1":
            products = self.db["products"]
            response = httpx.get(f"{self.settings.api_url.rstrip('/')}/api/v1/catalog/search", timeout=15)
            payload = response.json() if response.is_success else {}
            latency_ms = float(payload.get("latency_ms", 9999.0))
            return {"index_present": "search_text_1" in products.index_information(), "business_result": response.status_code == 200 and bool(payload.get("items")), "latency_within_recovery_threshold": latency_ms < self.settings.search_recovery_ms, "latency_ms": latency_ms}
        if proposal["action_key"] == "inventory.restore_capacity@1":
            time.sleep(5.2)
            order = httpx.post(
                f"{self.settings.api_url.rstrip('/')}/api/v1/orders",
                headers={"Idempotency-Key": f"verification-{new_id()}"},
                json={"sku": "sku-002", "quantity": 1},
                timeout=15,
            )
            health = httpx.get(f"{self.settings.inventory_url.rstrip('/')}/health", timeout=10).json()
            metrics = dict(health.get("metrics", {}))
            return {"capacity": health.get("capacity"), "business_result": order.status_code == 201, "error_rate": metrics.get("error_rate", 1.0), "p95_latency_ms": metrics.get("p95_latency_ms", 9999.0)}
        url = self.settings.worker_url
        health = httpx.get(f"{url.rstrip('/')}/health", timeout=10).json()
        desired = int(dict(proposal["parameters"])["desired"])
        if proposal["action_key"] == "worker.set_capacity@1":
            baseline = dict(proposal.get("backlog_baseline", {}))
            deadline = time.monotonic() + 90
            health = httpx.get(f"{url.rstrip('/')}/health", timeout=10).json()
            while time.monotonic() < deadline and int(health.get("oldest_age_seconds", 0)) >= 30:
                time.sleep(1.0)
                health = httpx.get(f"{url.rstrip('/')}/health", timeout=10).json()
            return {
                "capacity": health.get("capacity"),
                "business_result": int(health.get("queue_depth", 0)) < int(baseline.get("queue_depth", 0)),
                "queue_trending_down": int(health.get("queue_depth", 0)) < int(baseline.get("queue_depth", 0)),
                "oldest_age_below_30": int(health.get("oldest_age_seconds", 0)) < 30,
                "no_new_worker_errors": int(health.get("failures", 0)) <= int(baseline.get("failures", 0)),
            }
        business_result = bool(health.get("status") == "ok" and health.get("capacity") == desired)
        return {"capacity": health.get("capacity"), "business_result": business_result}

    @staticmethod
    def _verification_expectation(proposal: dict[str, object]) -> dict[str, object]:
        if proposal["action_key"] == "mongo.create_search_index@1":
            return {"index_present": True, "business_result": True, "latency_within_recovery_threshold": True}
        if proposal["action_key"] == "inventory.restore_capacity@1":
            return {"capacity": int(dict(proposal["parameters"])["desired"]), "business_result": True, "error_rate": 0.0}
        if proposal["action_key"] == "worker.set_capacity@1":
            return {"capacity": int(dict(proposal["parameters"])["desired"]), "business_result": True, "queue_trending_down": True, "oldest_age_below_30": True, "no_new_worker_errors": True}
        return {"capacity": int(dict(proposal["parameters"])["desired"]), "business_result": True}

    @staticmethod
    def _has_required_condition(category: str, evidence: list[dict[str, object]]) -> bool:
        if category == "catalog_search":
            observation = dict(evidence[0].get("observation", {}))
            return bool(observation.get("slow_operation") and observation.get("index_absent"))
        if category == "inventory_dependency":
            observation = dict(evidence[0].get("observation", {}))
            return bool(observation.get("reservation_failure") and observation.get("catalog_excluded") and observation.get("backlog_excluded"))
        return category == "order_backlog"

    def _advance_to(self, incident_id: str, target: IncidentState, reason: str) -> dict[str, object]:
        incident = self.incidents.get(incident_id)
        if incident["state"] == target.value:
            return incident
        self.logger.info("incident_lifecycle_transition", extra={"incident_id": incident_id, "target_state": target.value, "reason": reason})
        return self.incidents.advance(incident_id, target.value, f"orchestration-{target.value.lower()}-{new_id()}", actor="orchestrator", reason=reason)["incident"]

    @staticmethod
    def _risk_score(risk: str) -> int:
        return {"LOW": 1, "MEDIUM": 3}.get(risk, 99)
