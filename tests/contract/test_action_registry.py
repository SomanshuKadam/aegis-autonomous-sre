import pytest
from aegis.control.action_registry import validate_proposal

def test_action_registry_rejects_unknown_parameters_and_wrong_targets() -> None:
    with pytest.raises(ValueError): validate_proposal("inventory.restore_capacity@1", {"type": "order_worker"}, {})
    with pytest.raises(ValueError): validate_proposal("inventory.restore_capacity@1", {"type": "inventory_dependency"}, {"shell": "rm"})
