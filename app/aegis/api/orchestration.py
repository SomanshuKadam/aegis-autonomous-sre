from __future__ import annotations
from fastapi import APIRouter, Body, Depends
from typing import Literal
from pydantic import BaseModel, Field
from aegis.api.security import require_operator, require_orchestrator
from aegis.control.action_registry import resolve
from aegis.control.approvals import ApprovalStore
from aegis.control.policy import evaluate
from aegis.control.runner import RestrictedRunner
from aegis.control.incidents import IncidentStore
from aegis.control.verification import verify_profile
from aegis.control.rollback import RollbackGuard
from aegis.control.notifications import NotificationRecorder
from aegis.control.orchestrator import IncidentOrchestrator

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])
incidents = IncidentStore()
approvals = ApprovalStore(incidents)
runner = RestrictedRunner()
rollback_guard = RollbackGuard()
notifications = NotificationRecorder(incidents)
orchestrator = IncidentOrchestrator(incidents)

class AlertInput(BaseModel):
    source: str = Field(min_length=1)
    fingerprint: str = Field(min_length=1)
    category: str = Field(min_length=1)
    target: dict[str, object] = {}
    trace_id: str | None = Field(default=None, pattern="^[0-9a-f]{32}$")

class AdvanceInput(BaseModel):
    target_state: str = Field(min_length=1)
    command_id: str = Field(min_length=1)

class AgentAnalysisInput(BaseModel):
    incident_id: str = Field(pattern="^[0-9a-f]{32}$")
    trace_id: str = Field(pattern="^[0-9a-f]{32}$")
    category: Literal["catalog_search", "inventory_dependency", "order_backlog"]
    diagnosis: str = Field(min_length=1, max_length=1200)
    plausible_solution: str = Field(min_length=1, max_length=1200)
    evidence: list[str] = Field(min_length=1, max_length=8)
    selected_action: Literal[
        "mongo.create_search_index@1",
        "inventory.restore_capacity@1",
        "worker.set_capacity@1",
        "none",
    ]
    safe_to_proceed: bool

@router.post("/alerts", dependencies=[Depends(require_orchestrator)])
def ingest_alert(payload: AlertInput) -> dict[str, object]:
    from aegis.control.idempotency import dedup_key
    incident = incidents.create(payload.category, dedup_key(payload.source, payload.fingerprint, payload.category, payload.target), source=payload.source, fingerprint=payload.fingerprint, target=payload.target, trace_id=payload.trace_id)
    return {"disposition": "accepted", "incident_id": incident["incident_id"], "deduplicated": int(incident.get("alert_count", 1)) > 1}

@router.post("/incidents/{incident_id}/process", dependencies=[Depends(require_orchestrator)])
def process_incident(incident_id: str) -> dict[str, object]:
    result = orchestrator.process(incident_id)
    return {"incident_id": result.incident["incident_id"], "state": result.incident["state"], "outcome": result.outcome, "next_step": result.next_step}

@router.post("/incidents/{incident_id}/agent-analysis", dependencies=[Depends(require_orchestrator)])
def record_agent_analysis(incident_id: str, payload: AgentAnalysisInput) -> dict[str, object]:
    incident = incidents.get(incident_id)
    expected_actions = {
        "catalog_search": "mongo.create_search_index@1",
        "inventory_dependency": "inventory.restore_capacity@1",
        "order_backlog": "worker.set_capacity@1",
    }
    if payload.incident_id != incident_id:
        raise ValueError("agent analysis incident does not match the route")
    if payload.category != incident["category"]:
        raise ValueError("agent analysis category does not match the incident")
    if payload.trace_id != incident.get("trace_id"):
        raise ValueError("agent analysis trace does not match the source alert")
    expected_action = expected_actions[payload.category]
    if payload.safe_to_proceed and payload.selected_action != expected_action:
        raise ValueError("agent analysis selected an action outside the incident allowlist")
    if not payload.safe_to_proceed and payload.selected_action != "none":
        raise ValueError("unsafe agent analysis must not select an action")
    record = incidents.record(
        "agent_runs",
        incident_id,
        {
            "agent": "codex-signoz-investigator",
            "outcome": "SUPPORTED" if payload.safe_to_proceed else "INSUFFICIENT_EVIDENCE",
            **payload.model_dump(),
        },
    )
    return {
        "incident_id": incident_id,
        "accepted": True,
        "safe_to_proceed": record["safe_to_proceed"],
        "selected_action": record["selected_action"],
    }

@router.post("/incidents")
def create_incident(payload: dict = Body(...)) -> dict[str, object]:
    return incidents.create(str(payload["category"]), str(payload["dedup_key"]), source="manual", target=payload.get("target", {}))

@router.get("/incidents")
def list_incidents() -> dict[str, object]:
    return {"items": incidents.list()}

@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict[str, object]:
    return {**incidents.get(incident_id), **incidents.records(incident_id)}

@router.post("/incidents/{incident_id}/advance", dependencies=[Depends(require_orchestrator)])
def advance_incident(incident_id: str, payload: AdvanceInput) -> dict[str, object]:
    return incidents.advance(incident_id, payload.target_state, payload.command_id)

@router.post("/policy", dependencies=[Depends(require_orchestrator)])
def policy_check(payload: dict = Body(...)) -> dict[str, object]:
    action = resolve(str(payload["action_key"]))
    return evaluate(action, set(payload.get("evidence_types", [])), int(payload.get("risk_score", 0)))

@router.post("/approvals", dependencies=[Depends(require_operator)])
def request_approval(payload: dict = Body(...)) -> dict[str, object]:
    record = approvals.request(str(payload["incident_id"]), payload["proposal"])
    return {"approval_id": record["approval_id"], "expires_at": record["expires_at"]}

@router.post("/incidents/{incident_id}/approve", dependencies=[Depends(require_operator)])
def approve_incident(incident_id: str, payload: dict = Body(...)) -> dict[str, object]:
    result = orchestrator.approve(incident_id, str(payload["approval_id"]), str(payload.get("approver", "operator")), str(payload.get("decision", "APPROVED")))
    return {"incident_id": result.incident["incident_id"], "state": result.incident["state"], "outcome": result.outcome, "next_step": result.next_step}

@router.post("/execute", dependencies=[Depends(require_operator)])
def execute(payload: dict = Body(...)) -> dict[str, object]:
    approvals.consume(str(payload["approval_id"]), payload["proposal"])
    return runner.execute(payload["proposal"], payload.get("current_state"))

@router.post("/verify", dependencies=[Depends(require_operator)])
def verify_execution(payload: dict = Body(...)) -> dict[str, object]:
    return verify_profile(str(payload.get("profile", "exact_state")), payload.get("expected", {}), payload.get("observed", {}), bool(payload.get("fresh_business_result")), bool(payload.get("regression_free")))

@router.post("/rollback", dependencies=[Depends(require_operator)])
def rollback_execution(payload: dict = Body(...)) -> dict[str, object]:
    if payload.get("safe", True):
        return rollback_guard.compensate(str(payload["execution_id"]), payload.get("previous_state", {}))
    return rollback_guard.escalate(str(payload["execution_id"]), "rollback is not safe")

@router.post("/notifications", dependencies=[Depends(require_orchestrator)])
def record_notification(payload: dict = Body(...)) -> dict[str, object]:
    return notifications.record(str(payload["incident_id"]), str(payload.get("channel", "console")), bool(payload.get("delivered")), str(payload.get("detail", "")))
