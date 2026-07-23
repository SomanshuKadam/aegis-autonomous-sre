from __future__ import annotations

from aegis.control.evidence import fresh


def collect_catalog_evidence(trace_id: str, index_present: bool, latency_ms: float, observed_at, api_healthy: bool, mongo_healthy: bool) -> dict[str, object]:
    observations = [
        fresh("catalog-search-trace", {"trace_id": trace_id, "latency_ms": latency_ms}, observed_at),
        fresh("catalog-index-state", {"database": "mydatabase", "collection": "products", "field": "search_text", "index_present": index_present}, observed_at),
        fresh("catalog-dependencies", {"api_healthy": api_healthy, "mongo_healthy": mongo_healthy}, observed_at),
    ]
    root_cause = not index_present and latency_ms >= 2000 and api_healthy and mongo_healthy
    return {"evidence": observations, "root_cause": "missing_catalog_search_index" if root_cause else None, "competing_causes_excluded": api_healthy and mongo_healthy}
