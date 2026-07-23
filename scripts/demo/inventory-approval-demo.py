"""Manually demonstrate inventory saturation, exact approval, and fresh order recovery.

The driver uses only ordinary order creation to expose the bounded dependency condition. It then
submits the resulting incident through the normal control-plane API and approves the exact stored
proposal. It is a reviewer-operated local demonstration, not an automated test.
"""

from __future__ import annotations

import concurrent.futures
import os
from uuid import uuid4

import httpx


API_URL = os.getenv("AEGIS_API_URL", "http://api:8081").rstrip("/")


def create_order(sequence: int) -> int:
    response = httpx.post(
        f"{API_URL}/api/v1/orders",
        json={"sku": "sku-002", "quantity": 1},
        headers={"Idempotency-Key": f"inventory-demo-{uuid4()}-{sequence}"},
        timeout=15,
    )
    return response.status_code


def main() -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        statuses = list(pool.map(create_order, range(12)))
    failures = sum(status >= 400 for status in statuses)
    if failures == 0:
        raise RuntimeError("inventory condition was not exposed; increase concurrent demand before retrying")

    orchestrator_headers = {"Authorization": f"Bearer {os.environ['AEGIS_ORCHESTRATOR_TOKEN']}"}
    operator_headers = {"Authorization": f"Bearer {os.environ['AEGIS_OPERATOR_TOKEN']}"}
    fingerprint = f"inventory-demo-{uuid4()}"
    with httpx.Client(timeout=30) as client:
        alert = client.post(
            f"{API_URL}/api/v1/orchestration/alerts",
            headers=orchestrator_headers,
            json={"source": "manual-demo", "fingerprint": fingerprint, "category": "inventory_dependency", "target": {"type": "inventory_dependency"}},
        )
        alert.raise_for_status()
        incident_id = alert.json()["incident_id"]
        processed = client.post(f"{API_URL}/api/v1/orchestration/incidents/{incident_id}/process", headers=orchestrator_headers)
        processed.raise_for_status()
        if processed.json()["state"] != "APPROVAL_REQUIRED":
            raise RuntimeError(f"inventory lifecycle did not request approval: {processed.json()}")
        detail = client.get(f"{API_URL}/api/v1/orchestration/incidents/{incident_id}")
        detail.raise_for_status()
        approvals = detail.json().get("approvals", [])
        if len(approvals) != 1:
            raise RuntimeError("inventory lifecycle did not persist one exact approval")
        approved = client.post(
            f"{API_URL}/api/v1/orchestration/incidents/{incident_id}/approve",
            headers=operator_headers,
            json={"approval_id": approvals[0]["approval_id"], "approver": "manual-demo", "decision": "APPROVED"},
        )
        approved.raise_for_status()
        result = approved.json()
    if result["state"] != "RESOLVED":
        raise RuntimeError(f"inventory recovery did not resolve after fresh business verification: {result}")
    print(f"inventory-approval-manual-ok incident={incident_id} rejected_orders={failures}")


if __name__ == "__main__":
    main()
