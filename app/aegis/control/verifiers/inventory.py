from __future__ import annotations

def verify_inventory(reservation_succeeds: bool, healthy: bool, p95_ms: float, error_rate: float, catalog_healthy: bool = True, worker_healthy: bool = True) -> dict[str, object]:
    checks = {"fresh_reservation": reservation_succeeds, "inventory_healthy": healthy, "latency_under_1000_ms": p95_ms < 1000, "error_rate_under_1_percent": error_rate < 0.01, "catalog_unrelated": catalog_healthy, "worker_unrelated": worker_healthy}
    return {"outcome": "VERIFIED" if all(checks.values()) else "FAILED", "checks": checks}
