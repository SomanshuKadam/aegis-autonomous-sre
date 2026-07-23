from __future__ import annotations

def verify(expected: dict[str, object], observed: dict[str, object]) -> dict[str, object]:
    mismatches = {key: {"expected": value, "observed": observed.get(key)} for key, value in expected.items() if observed.get(key) != value}
    return {"outcome": "VERIFIED" if not mismatches else "FAILED", "mismatches": mismatches}

def verify_profile(profile: str, expected: dict[str, object], observed: dict[str, object], fresh_business_result: bool, regression_free: bool) -> dict[str, object]:
    result = verify(expected, observed)
    result.update({"profile": profile, "fresh_business_result": fresh_business_result, "regression_free": regression_free})
    if not fresh_business_result or not regression_free: result["outcome"] = "FAILED"
    return result
