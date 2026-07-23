import pytest
from aegis.control.budgets import InvestigationBudget

def test_budget_refuses_calls_after_limit() -> None:
    budget = InvestigationBudget(remaining_invocations=1); budget.consume_invocation()
    with pytest.raises(ValueError): budget.consume_invocation()
