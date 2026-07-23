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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aegis-runner"}
