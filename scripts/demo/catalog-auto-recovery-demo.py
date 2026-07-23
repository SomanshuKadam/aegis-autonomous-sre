"""Manually demonstrate catalog growth, telemetry-backed detection, and exact index recovery.

This reviewer-operated local walkthrough grows only temporary demo catalog rows, removes the one
registered index, performs a normal customer search, and submits the correlated signal through
the common lifecycle. It has no customer-facing failure or repair control.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from pymongo import MongoClient


API_URL = os.getenv("AEGIS_API_URL", "http://api:8081").rstrip("/")


def main() -> None:
    run_id = f"catalog-demo-{uuid4().hex}"
    client = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=5000)
    products = client[os.getenv("MONGO_DATABASE", "mydatabase")]["products"]
    products.insert_many(
        [
            {
                "product_id": f"{run_id}-{item}",
                "sku": f"{run_id}-{item}",
                "name": f"Aegis catalog growth item {item}",
                "search_text": f"aegis catalog growth {item}",
                "price_minor": 1000 + item,
                "demo_run_id": run_id,
                "created_at": datetime.now(timezone.utc),
            }
            for item in range(80)
        ]
    )
    if "search_text_1" in products.index_information():
        products.drop_index("search_text_1")

    headers = {"Authorization": f"Bearer {os.environ['AEGIS_ORCHESTRATOR_TOKEN']}"}
    with httpx.Client(timeout=30) as http:
        search = http.get(f"{API_URL}/api/v1/catalog/search")
        search.raise_for_status()
        signal = search.json()
        if signal.get("index_present") or float(signal.get("latency_ms", 0)) < 2000 or len(str(signal.get("trace_id", ""))) != 32:
            raise RuntimeError(f"catalog search did not expose the expected telemetry signal: {signal}")
        alert = http.post(
            f"{API_URL}/api/v1/orchestration/alerts",
            headers=headers,
            json={
                "source": "signoz-manual-demo",
                "fingerprint": run_id,
                "category": "catalog_search",
                "target": {"type": "mongodb_collection", "database": "mydatabase", "collection": "products", "field": "search_text"},
                "trace_id": signal["trace_id"],
            },
        )
        alert.raise_for_status()
        incident_id = alert.json()["incident_id"]
        processed = http.post(f"{API_URL}/api/v1/orchestration/incidents/{incident_id}/process", headers=headers)
        processed.raise_for_status()
        if processed.json().get("state") != "RESOLVED":
            raise RuntimeError(f"catalog recovery did not resolve: {processed.json()}")
        detail = http.get(f"{API_URL}/api/v1/orchestration/incidents/{incident_id}")
        detail.raise_for_status()
    evidence = detail.json().get("evidence", [])
    if not any(item.get("observation", {}).get("trace_id") == signal["trace_id"] and item.get("observation", {}).get("slow_operation") for item in evidence):
        raise RuntimeError("catalog recovery did not retain the real slow-search evidence")
    if "search_text_1" not in products.index_information():
        raise RuntimeError("catalog lifecycle did not create the exact registered index")
    print(f"catalog-auto-recovery-manual-ok incident={incident_id} trace={signal['trace_id']}")


if __name__ == "__main__":
    main()
