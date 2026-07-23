from __future__ import annotations

def verify_inventory(reservation_succeeds: bool, healthy: bool, p95_ms: float, error_rate: float) -> dict[str, object]:
    passed = reservation_succeeds and healthy and p95_ms < 1000 and error_rate < 0.01
    return {"outcome": "VERIFIED" if passed else "FAILED"}
