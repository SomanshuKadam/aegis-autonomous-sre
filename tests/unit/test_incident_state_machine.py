import pytest
from aegis.control.models import IncidentState
from aegis.control.state_machine import TERMINAL, transition


def test_allows_detected_to_validating() -> None:
    assert transition(IncidentState.DETECTED, IncidentState.VALIDATING) is IncidentState.VALIDATING


def test_rejects_terminal_transition() -> None:
    for state in TERMINAL:
        with pytest.raises(ValueError): transition(state, IncidentState.EXECUTING)
