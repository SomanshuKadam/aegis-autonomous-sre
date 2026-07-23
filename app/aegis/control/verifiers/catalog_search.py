from __future__ import annotations

def verify_catalog_search(index_present: bool, latency_ms: float, fresh_result: bool) -> dict[str, object]:
    passed = index_present and latency_ms < 2000 and fresh_result
    return {"outcome": "VERIFIED" if passed else "FAILED", "checks": {"index_present": index_present, "latency_under_2000_ms": latency_ms < 2000, "fresh_result": fresh_result}}
