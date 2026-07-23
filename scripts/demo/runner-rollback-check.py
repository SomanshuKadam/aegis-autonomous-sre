"""Manually prove a registered capacity action records and restores its prior state.

Run this only against the local Compose network. It performs one bounded inventory capacity
increase through the restricted runner, invokes the runner's compensating endpoint once, and
prints a non-secret success marker.
"""

from __future__ import annotations

import os

import httpx


def main() -> None:
    headers = {"Authorization": f"Bearer {os.environ['AEGIS_RUNNER_TOKEN']}"}
    proposal = {
        "proposal_id": "manual-runner-rollback-check",
        "incident_id": "manual-runner-rollback-check",
        "action_key": "inventory.restore_capacity@1",
        "target": {"type": "inventory_dependency"},
        "parameters": {"desired": 2},
        "desired_state": {"desired": 2},
        "evidence_version": 1,
        "idempotency_key": "manual-runner-rollback-check",
    }
    with httpx.Client(timeout=15) as client:
        executed = client.post("http://action-runner:8085/actions/execute", headers=headers, json={"proposal": proposal})
        executed.raise_for_status()
        result = executed.json()
        if result.get("state") == "DUPLICATE":
            raise RuntimeError("use a new manual idempotency key after an interrupted check")
        previous = result.get("previous_state", {})
        if result.get("state") != "SUCCEEDED" or previous.get("desired") != 1:
            raise RuntimeError("registered capacity action did not capture the expected prior state")
        rollback = client.post(
            "http://action-runner:8085/actions/rollback",
            headers=headers,
            json={"action_key": proposal["action_key"], "target": proposal["target"], "previous_state": previous},
        )
        rollback.raise_for_status()
        health = client.get("http://inventory:8082/health").json()
    if rollback.json().get("state") != "SUCCEEDED" or health.get("capacity") != previous["desired"]:
        raise RuntimeError("registered compensation did not restore inventory capacity")
    print("runner-rollback-manual-ok")


if __name__ == "__main__":
    main()
