from __future__ import annotations

from aegis.control.models import IncidentState
from aegis.control.state_machine import transition
from aegis.control.timeline import event
from aegis.control.budgets import InvestigationBudget
from aegis.control.agents import evaluate_hypotheses, plan


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

    def investigate(self, incident: dict[str, object], evidence: list[dict[str, object]], budget: InvestigationBudget) -> dict[str, object]:
        while incident["state"] in {IncidentState.DETECTED.value, IncidentState.VALIDATING.value, IncidentState.ENRICHING.value}:
            self.progress(incident)
        findings = evaluate_hypotheses(evidence, budget)
        if findings["outcome"] != "ROOT_CAUSE_IDENTIFIED":
            return self.advance(incident, IncidentState.BLOCKED, "investigator")
        self.advance(incident, IncidentState.ROOT_CAUSE_IDENTIFIED, "investigator")
        proposal = plan(str(incident["category"]), evidence, budget)
        incident["proposal"] = proposal
        return self.advance(incident, IncidentState.ACTION_PROPOSED if proposal["outcome"] == "ACTION_PROPOSED" else IncidentState.BLOCKED, "planner")
