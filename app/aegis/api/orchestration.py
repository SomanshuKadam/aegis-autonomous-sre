from __future__ import annotations
from fastapi import APIRouter, Body, Depends
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

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])
approvals = ApprovalStore()
runner = RestrictedRunner()
incidents = IncidentStore()
rollback_guard = RollbackGuard()
notifications = NotificationRecorder()

class AlertInput(BaseModel):
    source: str = Field(min_length=1)
    fingerprint: str = Field(min_length=1)
    category: str = Field(min_length=1)
    target: dict[str, object] = {}

@router.post("/alerts", dependencies=[Depends(require_orchestrator)])
def ingest_alert(payload: AlertInput) -> dict[str, object]:
    from aegis.control.idempotency import dedup_key
    incident = incidents.create(payload.category, dedup_key(payload.source, payload.fingerprint, payload.category, payload.target))
    return {"disposition": "accepted", "incident_id": incident["incident_id"], "deduplicated": len(incident["timeline"]) > 0}

@router.post("/incidents")
def create_incident(payload: dict = Body(...)) -> dict[str, object]:
    return incidents.create(str(payload["category"]), str(payload["dedup_key"]))

@router.get("/incidents")
def list_incidents() -> dict[str, object]:
    return {"items": list(incidents.items.values())}

@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict[str, object]:
    return incidents.items[incident_id]

@router.post("/incidents/{incident_id}/advance", dependencies=[Depends(require_orchestrator)])
def advance_incident(incident_id: str, payload: dict = Body(...)) -> dict[str, object]:
    return incidents.advance(incident_id, str(payload["target_state"]))

@router.post("/policy", dependencies=[Depends(require_orchestrator)])
def policy_check(payload: dict = Body(...)) -> dict[str, object]:
    action = resolve(str(payload["action_key"]))
    return evaluate(action, set(payload.get("evidence_types", [])), int(payload.get("risk_score", 0)))

@router.post("/approvals", dependencies=[Depends(require_operator)])
def request_approval(payload: dict = Body(...)) -> dict[str, object]:
    record = approvals.request(payload)
    return {"approval_id": record.approval_id, "expires_at": record.expires_at}

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

@router.post("/notifications")
def record_notification(payload: dict = Body(...)) -> dict[str, object]:
    return notifications.record(str(payload["incident_id"]), str(payload.get("channel", "console")), bool(payload.get("delivered")))
