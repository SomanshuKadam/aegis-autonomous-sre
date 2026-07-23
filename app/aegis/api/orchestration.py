from __future__ import annotations
from fastapi import APIRouter, Depends
from aegis.api.security import require_orchestrator

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])

@router.post("/alerts", dependencies=[Depends(require_orchestrator)])
def ingest_alert() -> dict[str, str]: return {"disposition":"accepted"}
