from __future__ import annotations
import hmac
from fastapi import Header, HTTPException, status
from aegis.config import get_settings
def require_orchestrator(authorization: str | None = Header(default=None)) -> None:
    token = authorization.removeprefix("Bearer ") if authorization else ""
    expected = get_settings().orchestrator_token.get_secret_value()
    if not expected or not hmac.compare_digest(token, expected): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid orchestrator credentials")
def require_operator(authorization: str | None = Header(default=None)) -> None:
    token = authorization.removeprefix("Bearer ") if authorization else ""
    expected = get_settings().operator_token.get_secret_value()
    if not expected or not hmac.compare_digest(token, expected): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid operator credentials")
