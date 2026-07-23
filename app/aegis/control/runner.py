from __future__ import annotations
from aegis.control.action_registry import validate_proposal
from aegis.control.idempotency import desired_state_satisfied, operation_key

class RestrictedRunner:
    def __init__(self) -> None: self.claimed: set[str] = set()
    def execute(self, proposal: dict[str, object], current_state: dict[str, object] | None = None) -> dict[str, object]:
        target = proposal.get("target", {})
        action = validate_proposal(str(proposal["action_key"]), target, proposal.get("parameters", {}))
        desired = proposal.get("desired_state", proposal.get("parameters", {}))
        if current_state is not None and desired_state_satisfied(current_state, desired):
            return {"state": "NOOP", "action": action.action_id, "target": target}
        claim = operation_key(str(proposal.get("incident_id", "manual")), action.action_id, proposal.get("parameters", {}), int(proposal.get("evidence_version", 1)))
        if claim in self.claimed:
            return {"state": "DUPLICATE", "action": action.action_id, "target": target}
        self.claimed.add(claim)
        return {"state": "SUCCEEDED", "action": action.action_id, "target": target}
