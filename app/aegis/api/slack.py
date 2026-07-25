"""Verified Slack interactive approval ingress."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qs

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from aegis.config import get_settings


router = APIRouter(tags=["slack"])
logger = logging.getLogger(__name__)
_MAX_SIGNATURE_AGE_SECONDS = 300
_ACTIONS = {
    "aegis_approval_approve": ("DECIDE", "APPROVED"),
    "aegis_approval_reject": ("DECIDE", "REJECTED"),
    "aegis_approval_reopen": ("REOPEN", ""),
}


def _verify_request(raw_body: bytes, timestamp: str | None, signature: str | None) -> None:
    secret = get_settings().slack_signing_secret.get_secret_value()
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Slack interactions are not configured")
    if not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing Slack signature")
    try:
        sent_at = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid Slack timestamp") from exc
    if abs(int(time.time()) - sent_at) > _MAX_SIGNATURE_AGE_SECONDS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="expired Slack request")
    base = f"v0:{timestamp}:{raw_body.decode('utf-8')}".encode("utf-8")
    expected = "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid Slack signature")


async def _forward_interaction(forward_url: str, payload: dict[str, str]) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(forward_url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError:
        logger.exception(
            "Slack approval handoff failed",
            extra={
                "incident_id": payload.get("incident_id"),
                "operation": payload.get("operation"),
            },
        )


@router.post("/api/v1/slack/interactions")
async def handle_interaction(
    request: Request,
    background_tasks: BackgroundTasks,
    x_slack_request_timestamp: str | None = Header(default=None),
    x_slack_signature: str | None = Header(default=None),
) -> JSONResponse:
    raw_body = await request.body()
    _verify_request(raw_body, x_slack_request_timestamp, x_slack_signature)
    encoded = parse_qs(raw_body.decode("utf-8"))
    try:
        payload = json.loads(encoded["payload"][0])
        action = payload["actions"][0]
        operation, decision = _ACTIONS[str(action["action_id"])]
        reference = json.loads(str(action["value"]))
        incident_id = str(reference["incident_id"])
        approval_id = str(reference["approval_id"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported Slack interaction payload") from exc
    if len(incident_id) != 32 or len(approval_id) != 32:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid approval reference")
    user = payload.get("user", {})
    approver = str(user.get("username") or user.get("name") or user.get("id") or "slack-operator")
    forward_payload = {
        "operation": operation,
        "incident_id": incident_id,
        "approval_id": approval_id,
        "approver": approver,
    }
    if operation == "DECIDE":
        forward_payload["decision"] = decision
    forward_url = get_settings().slack_interaction_forward_url
    background_tasks.add_task(_forward_interaction, forward_url, forward_payload)
    if operation == "REOPEN":
        return JSONResponse({
            "replace_original": True,
            "text": f"Aegis approval reopen request received from {approver}",
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*Reopen request received*\n<@{user.get('id', approver)}> requested a fresh approval window for incident `{incident_id}`."}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": "Aegis is validating the unchanged proposal and will post a new approval card."}]},
            ],
        })
    verb = "approved" if decision == "APPROVED" else "rejected"
    return JSONResponse({
        "replace_original": True,
        "text": f"Aegis remediation decision received from {approver}",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Decision received*\n<@{user.get('id', approver)}> {verb} the proposed remediation for incident `{incident_id}`."}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "Aegis is processing the decision and will post the verified outcome."}]},
        ],
    })
