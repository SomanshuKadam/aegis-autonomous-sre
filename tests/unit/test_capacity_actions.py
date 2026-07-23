from aegis.control.actions.inventory_capacity import restore_capacity
from aegis.control.actions.worker_capacity import increase_capacity
from aegis.control.verifiers.backlog import verify_backlog
from aegis.control.verifiers.inventory import verify_inventory
from aegis.inventory.capacity import CapacityState
from aegis.worker.capacity import WorkerCapacity

def test_capacity_handlers_and_fresh_verifiers() -> None:
    assert restore_capacity(CapacityState(), 2)["desired"] == 2
    assert increase_capacity(WorkerCapacity(), 2)["desired"] == 3
    assert verify_inventory(True, True, 500, 0.001)["outcome"] == "VERIFIED"
    assert verify_backlog(10, 2, False)["outcome"] == "VERIFIED"
