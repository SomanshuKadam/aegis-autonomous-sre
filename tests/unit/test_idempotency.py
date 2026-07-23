from aegis.control.idempotency import desired_state_satisfied, operation_key

def test_desired_state_noop_and_operation_key_are_deterministic() -> None:
    assert desired_state_satisfied({"desired": 2, "other": 1}, {"desired": 2})
    assert not desired_state_satisfied({"desired": 1}, {"desired": 2})
    assert operation_key("i", "a", {"x": 1}, 1) == operation_key("i", "a", {"x": 1}, 1)
