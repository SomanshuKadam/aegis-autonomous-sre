from __future__ import annotations

from aegis.control.evidence import fresh


def classify_inventory(healthy: bool, p95_ms: float, error_rate: float, catalog_healthy: bool, worker_healthy: bool, observed_at) -> dict[str, object]:
    evidence = fresh("inventory-dependency", {"healthy": healthy, "p95_ms": p95_ms, "error_rate": error_rate}, observed_at)
    affected = (not healthy) or p95_ms >= 1000 or error_rate >= 0.01
    return {"evidence": evidence, "root_cause": "inventory_dependency" if affected and catalog_healthy and worker_healthy else None, "catalog_excluded": catalog_healthy, "backlog_excluded": worker_healthy}
