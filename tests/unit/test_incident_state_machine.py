import pytest
from aegis.control.models import IncidentState
from aegis.control.state_machine import transition


def test_allows_detected_to_validating() -> None:
    assert transition(IncidentState.DETECTED, IncidentState.VALIDATING) is IncidentState.VALIDATING


def test_rejects_terminal_transition() -> None:
    with pytest.raises(ValueError):
        transition(IncidentState.RESOLVED, IncidentState.EXECUTING)
