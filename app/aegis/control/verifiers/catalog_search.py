from __future__ import annotations

def verify_catalog_search(index_present: bool, latency_ms: float, fresh_result: bool, api_healthy: bool = True, mongo_healthy: bool = True) -> dict[str, object]:
    passed = index_present and latency_ms < 2000 and fresh_result and api_healthy and mongo_healthy
    return {"outcome": "VERIFIED" if passed else "FAILED", "checks": {"exact_index_present": index_present, "latency_under_2000_ms": latency_ms < 2000, "fresh_result": fresh_result, "api_healthy": api_healthy, "mongo_healthy": mongo_healthy}}
