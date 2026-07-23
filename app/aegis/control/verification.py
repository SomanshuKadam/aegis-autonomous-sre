from __future__ import annotations

def verify(expected: dict[str, object], observed: dict[str, object]) -> dict[str, object]:
    mismatches = {key: {"expected": value, "observed": observed.get(key)} for key, value in expected.items() if observed.get(key) != value}
    return {"outcome": "VERIFIED" if not mismatches else "FAILED", "mismatches": mismatches}
