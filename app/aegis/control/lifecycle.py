from __future__ import annotations

from aegis.control.models import IncidentState
from aegis.control.state_machine import transition
from aegis.control.timeline import event


class IncidentLifecycle:
    """Applies validated incident transitions and records the resulting timeline event."""

    def advance(self, incident: dict[str, object], target: IncidentState, actor: str) -> dict[str, object]:
        source = IncidentState(str(incident["state"]))
        incident["state"] = transition(source, target).value
        sequence = int(incident.get("timeline_sequence", 0)) + 1
        incident["timeline_sequence"] = sequence
        incident.setdefault("timeline", []).append(event(str(incident["incident_id"]), sequence, target.value, "technical", "advanced", actor))
        return incident

    def progress(self, incident: dict[str, object], actor: str = "orchestrator") -> dict[str, object]:
        """Advance one deterministic stage until an external decision is required."""
        current = IncidentState(str(incident["state"]))
        next_state = {
            IncidentState.DETECTED: IncidentState.VALIDATING,
            IncidentState.VALIDATING: IncidentState.ENRICHING,
            IncidentState.ENRICHING: IncidentState.INVESTIGATING,
            IncidentState.INVESTIGATING: IncidentState.ROOT_CAUSE_IDENTIFIED,
            IncidentState.ROOT_CAUSE_IDENTIFIED: IncidentState.ACTION_PROPOSED,
            IncidentState.ACTION_PROPOSED: IncidentState.POLICY_CHECKED,
        }.get(current)
        return self.advance(incident, next_state, actor) if next_state else incident
