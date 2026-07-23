import pytest
from aegis.control.rollback import RollbackGuard
from aegis.control.verification import verify
from aegis.inventory.capacity import CapacityState

def test_verification_rollback_and_capacity_bounds() -> None:
    assert verify({"state": "healthy"}, {"state": "healthy"})["outcome"] == "VERIFIED"
    guard = RollbackGuard(); assert guard.compensate("execution-1", {"desired": 1})["outcome"] == "ROLLED_BACK"
    with pytest.raises(ValueError): guard.compensate("execution-1", {"desired": 1})
    with pytest.raises(ValueError): CapacityState().restore(9)
