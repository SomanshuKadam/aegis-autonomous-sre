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
    orchestrator_headers = {"Authorization": f"Bearer {os.environ['AEGIS_ORCHESTRATOR_TOKEN']}"}
    operator_headers = {"Authorization": f"Bearer {os.environ['AEGIS_OPERATOR_TOKEN']}"}
    runner_headers = {"Authorization": f"Bearer {os.environ['AEGIS_RUNNER_TOKEN']}"}
    preparation: tuple[dict[str, object], dict[str, object]] | None = None
    with httpx.Client(timeout=30) as client:
        initial = client.get("http://inventory:8082/health").json()
        initial_capacity = int(initial["capacity"])
        try:
            if initial_capacity != 1:
                preparation_proposal = {
                    "proposal_id": f"inventory-demo-baseline-{uuid4()}",
                    "incident_id": "manual-inventory-baseline",
                    "action_key": "inventory.restore_capacity@1",
                    "target": {"type": "inventory_dependency"},
                    "parameters": {"desired": 1},
                    "desired_state": {"desired": 1},
                    "evidence_version": 1,
                    "idempotency_key": f"inventory-demo-baseline-{uuid4()}",
                }
                prepared = client.post("http://action-runner:8085/actions/execute", headers=runner_headers, json={"proposal": preparation_proposal})
                prepared.raise_for_status()
                preparation_result = prepared.json()
                if preparation_result.get("state") not in {"SUCCEEDED", "NOOP"}:
                    raise RuntimeError("restricted runner did not establish the bounded inventory baseline")
                preparation = (preparation_proposal, preparation_result)

            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
                statuses = list(pool.map(create_order, range(12)))
            failures = sum(status >= 400 for status in statuses)
            if failures == 0:
                raise RuntimeError("inventory condition was not exposed; increase concurrent demand before retrying")

            alert = client.post(
                f"{API_URL}/api/v1/orchestration/alerts",
                headers=orchestrator_headers,
                json={"source": "manual-demo", "fingerprint": f"inventory-demo-{uuid4()}", "category": "inventory_dependency", "target": {"type": "inventory_dependency"}},
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
        finally:
            if preparation:
                proposal, prepared = preparation
                restored = client.post(
                    "http://action-runner:8085/actions/rollback",
                    headers=runner_headers,
                    json={"action_key": proposal["action_key"], "target": proposal["target"], "previous_state": prepared["previous_state"], "idempotency_key": proposal["idempotency_key"]},
                )
                restored.raise_for_status()
                if int(client.get("http://inventory:8082/health").json()["capacity"]) != initial_capacity:
                    raise RuntimeError("manual inventory baseline was not restored")
    if result["state"] != "RESOLVED":
        raise RuntimeError(f"inventory recovery did not resolve after fresh business verification: {result}")
    print(f"inventory-approval-manual-ok incident={incident_id} rejected_orders={failures}")


if __name__ == "__main__":
    main()
