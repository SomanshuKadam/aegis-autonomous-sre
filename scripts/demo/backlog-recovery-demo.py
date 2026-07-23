"""Manually demonstrate a real order backlog and one bounded worker-capacity recovery."""

from __future__ import annotations

import os
import time
import concurrent.futures
from uuid import uuid4

import httpx


API_URL = os.getenv("AEGIS_API_URL", "http://api:8081").rstrip("/")
WORKER_URL = os.getenv("AEGIS_WORKER_URL", "http://worker:8083").rstrip("/")


def main() -> None:
    with httpx.Client(timeout=20) as client:
        initial = client.get(f"{WORKER_URL}/health").json()
        if int(initial["capacity"]) >= int(initial["maximum"]):
            raise RuntimeError("worker is already at maximum capacity; run the safe-refusal walkthrough instead")
        def create_order(item: int) -> None:
            for attempt in range(20):
                response = httpx.post(
                    f"{API_URL}/api/v1/orders",
                    json={"sku": "sku-001", "quantity": 1},
                    headers={"Idempotency-Key": f"backlog-demo-{uuid4()}-{item}-{attempt}"},
                    timeout=20,
                )
                if response.status_code == 201:
                    return
                if response.status_code not in {409, 503}:
                    response.raise_for_status()
                time.sleep(0.15)
            raise RuntimeError("inventory did not accept the bounded backlog demand after retries")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(create_order, range(int(initial["capacity"]) * 60)))
        deadline = time.monotonic() + 45
        health = client.get(f"{WORKER_URL}/health").json()
        while time.monotonic() < deadline and not (int(health["queue_depth"]) > 0 and int(health["oldest_age_seconds"]) >= 30):
            time.sleep(1)
            health = client.get(f"{WORKER_URL}/health").json()
        if not (int(health["queue_depth"]) > 0 and int(health["oldest_age_seconds"]) >= 30):
            raise RuntimeError(f"demand peak did not form an aged queue: {health}")

        headers = {"Authorization": f"Bearer {os.environ['AEGIS_ORCHESTRATOR_TOKEN']}"}
        alert = client.post(
            f"{API_URL}/api/v1/orchestration/alerts",
            headers=headers,
            json={"source": "manual-demo", "fingerprint": f"backlog-demo-{uuid4()}", "category": "order_backlog", "target": {"type": "order_worker"}},
        )
        alert.raise_for_status()
        incident_id = alert.json()["incident_id"]
        processed = client.post(f"{API_URL}/api/v1/orchestration/incidents/{incident_id}/process", headers=headers)
        processed.raise_for_status()
        result = processed.json()
    if result["state"] != "RESOLVED":
        raise RuntimeError(f"backlog recovery did not resolve through fresh queue verification: {result}")
    print(f"backlog-recovery-manual-ok incident={incident_id} capacity={initial['capacity']}->{int(initial['capacity']) + 1}")


if __name__ == "__main__":
    main()
