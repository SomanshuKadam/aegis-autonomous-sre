from __future__ import annotations

def verify_backlog(depth_before: int, depth_after: int, errors_increased: bool, oldest_age_seconds: int = 0, headroom: bool = True) -> dict[str, object]:
    checks = {"depth_decreased": depth_after < depth_before, "errors_stable": not errors_increased, "oldest_age_under_30_seconds": oldest_age_seconds < 30, "resource_headroom": headroom}
    return {"outcome": "VERIFIED" if all(checks.values()) else "FAILED", "checks": checks}
