import pytest
from aegis.control.approvals import ApprovalStore

def test_approval_is_bound_and_one_use() -> None:
    proposal = {"action_key": "inventory.restore_capacity@1", "target": {"type": "inventory_dependency"}}
    store = ApprovalStore(); approval = store.request(proposal); store.consume(approval.approval_id, proposal)
    with pytest.raises(ValueError): store.consume(approval.approval_id, proposal)
