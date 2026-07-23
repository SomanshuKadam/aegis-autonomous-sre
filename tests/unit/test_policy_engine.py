from aegis.control.action_registry import resolve
from aegis.control.policy import evaluate

def test_policy_requires_evidence_and_approval_for_medium_risk() -> None:
    action = resolve("inventory.restore_capacity@1")
    assert evaluate(action, set(), 1)["outcome"] == "BLOCKED"
    assert evaluate(action, {"inventory_health"}, 3)["outcome"] == "APPROVAL_REQUIRED"
    assert evaluate(action, {"inventory_health"}, 10)["outcome"] == "PROHIBITED"
