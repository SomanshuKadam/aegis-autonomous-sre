"""Manually prove a registered capacity action records and restores its prior state.

Run this only against the local Compose network. It performs one bounded inventory capacity
increase through the restricted runner, invokes the runner's compensating endpoint once, and
prints a non-secret success marker.
"""

from __future__ import annotations

import os
from uuid import uuid4

import httpx


def main() -> None:
    headers = {"Authorization": f"Bearer {os.environ['AEGIS_RUNNER_TOKEN']}"}
    check_id = f"manual-runner-rollback-{uuid4().hex}"
    with httpx.Client(timeout=15) as client:
        before = client.get("http://inventory:8082/health").json()
        previous_capacity = int(before["capacity"])
        maximum = int(before["maximum"])
        desired = previous_capacity + 1 if previous_capacity < maximum else previous_capacity - 1
        if desired < 1:
            raise RuntimeError("inventory capacity cannot be changed safely for this manual check")
        proposal = {
            "proposal_id": check_id,
            "incident_id": check_id,
            "action_key": "inventory.restore_capacity@1",
            "target": {"type": "inventory_dependency"},
            "parameters": {"desired": desired},
            "desired_state": {"desired": desired},
            "evidence_version": 1,
            "idempotency_key": check_id,
        }
        executed = client.post("http://action-runner:8085/actions/execute", headers=headers, json={"proposal": proposal})
        executed.raise_for_status()
        result = executed.json()
        if result.get("state") == "DUPLICATE":
            raise RuntimeError("use a new manual idempotency key after an interrupted check")
        previous = result.get("previous_state", {})
        if result.get("state") != "SUCCEEDED" or previous.get("desired") != previous_capacity:
            raise RuntimeError("registered capacity action did not capture the expected prior state")
        rollback = client.post(
            "http://action-runner:8085/actions/rollback",
            headers=headers,
            json={"action_key": proposal["action_key"], "target": proposal["target"], "previous_state": previous, "idempotency_key": proposal["idempotency_key"]},
        )
        rollback.raise_for_status()
        duplicate_rollback = client.post(
            "http://action-runner:8085/actions/rollback",
            headers=headers,
            json={"action_key": proposal["action_key"], "target": proposal["target"], "previous_state": previous, "idempotency_key": proposal["idempotency_key"]},
        )
        health = client.get("http://inventory:8082/health").json()
    if rollback.json().get("state") != "SUCCEEDED" or duplicate_rollback.status_code != 400 or health.get("capacity") != previous["desired"]:
        raise RuntimeError("registered compensation did not restore inventory capacity")
    print("runner-rollback-manual-ok")


if __name__ == "__main__":
    main()
