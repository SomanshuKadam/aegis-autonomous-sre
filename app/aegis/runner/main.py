from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from aegis.config import get_settings
from aegis.control.action_executor import ActionExecutor

app = FastAPI(title="Aegis Restricted Runner")
executor = ActionExecutor()

class ActionRequest(BaseModel):
    proposal: dict[str, object]

@app.post("/actions/execute")
def execute(payload: ActionRequest, authorization: str | None = Header(default=None)) -> dict[str, object]:
    token = authorization.removeprefix("Bearer ") if authorization else ""
    if token != get_settings().runner_token.get_secret_value():
        raise HTTPException(status_code=401, detail="invalid runner credentials")
    return executor.execute(payload.proposal)


class RollbackRequest(BaseModel):
    action_key: str
    target: dict[str, object]
    previous_state: dict[str, object]
    idempotency_key: str


@app.post("/actions/rollback")
def rollback(payload: RollbackRequest, authorization: str | None = Header(default=None)) -> dict[str, object]:
    token = authorization.removeprefix("Bearer ") if authorization else ""
    if token != get_settings().runner_token.get_secret_value():
        raise HTTPException(status_code=401, detail="invalid runner credentials")
    return executor.rollback(payload.action_key, payload.target, payload.previous_state, payload.idempotency_key)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aegis-runner"}
