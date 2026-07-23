from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException
from aegis.control.fixtures import load_fixture
from aegis.control.replay import evaluate_fixture

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])

@router.get("/replays/{fixture_id}")
def replay(fixture_id: str) -> dict[str, object]:
    path = Path("/app/tests/replay/fixtures") / f"{fixture_id}.json"
    if not path.exists(): raise HTTPException(status_code=404, detail="replay fixture not found")
    return evaluate_fixture(load_fixture(path))
