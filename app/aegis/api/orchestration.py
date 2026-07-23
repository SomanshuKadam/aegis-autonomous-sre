from __future__ import annotations
from fastapi import APIRouter, Body, Depends
from aegis.api.security import require_operator, require_orchestrator
from aegis.control.action_registry import resolve
from aegis.control.approvals import ApprovalStore
from aegis.control.policy import evaluate
from aegis.control.runner import RestrictedRunner

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])
approvals = ApprovalStore()
runner = RestrictedRunner()

@router.post("/alerts", dependencies=[Depends(require_orchestrator)])
def ingest_alert() -> dict[str, str]: return {"disposition":"accepted"}

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
    return runner.execute(payload["proposal"])
