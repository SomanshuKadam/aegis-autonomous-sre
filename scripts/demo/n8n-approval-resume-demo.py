"""Manually prove n8n resumes an exact inventory approval and records notification state."""
from __future__ import annotations

import concurrent.futures
import os
import time
from uuid import uuid4

import httpx

API = os.getenv("AEGIS_API_URL", "http://api:8081").rstrip("/")


def order(_: int) -> int:
    return httpx.post(f"{API}/api/v1/orders", json={"sku": "sku-002", "quantity": 1}, headers={"Idempotency-Key": f"n8n-approval-{uuid4()}"}, timeout=15).status_code


def main() -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        if not any(status >= 400 for status in pool.map(order, range(16))):
            raise RuntimeError("inventory condition was not exposed")
    headers = {"Authorization": f"Bearer {os.environ['AEGIS_ORCHESTRATOR_TOKEN']}"}
    with httpx.Client(timeout=30) as client:
        created = client.post(f"{API}/api/v1/orchestration/alerts", headers=headers, json={"source": "manual-demo", "fingerprint": f"n8n-approval-{uuid4()}", "category": "inventory_dependency", "target": {"type": "inventory_dependency"}})
        created.raise_for_status(); incident_id = created.json()["incident_id"]
        processed = client.post(f"{API}/api/v1/orchestration/incidents/{incident_id}/process", headers=headers)
        processed.raise_for_status()
        if processed.json()["state"] != "APPROVAL_REQUIRED": raise RuntimeError("inventory incident did not require approval")
        detail = client.get(f"{API}/api/v1/orchestration/incidents/{incident_id}").json()
        resumed = client.post("http://n8n:5678/webhook/approval-resume", json={"incident_id": incident_id, "approval_id": detail["approvals"][0]["approval_id"], "approver": "n8n-manual-demo", "decision": "APPROVED"})
        resumed.raise_for_status()
        time.sleep(7)
        final = client.get(f"{API}/api/v1/orchestration/incidents/{incident_id}").json()
    if final["state"] != "RESOLVED" or not final["notifications"]: raise RuntimeError("n8n approval branch did not resolve and record notification")
    print(f"n8n-approval-resume-manual-ok incident={incident_id}")


if __name__ == "__main__": main()
