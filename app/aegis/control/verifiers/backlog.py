from __future__ import annotations

def verify_backlog(depth_before: int, depth_after: int, errors_increased: bool) -> dict[str, object]:
    return {"outcome": "VERIFIED" if depth_after < depth_before and not errors_increased else "FAILED"}
