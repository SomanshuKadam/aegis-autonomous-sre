from __future__ import annotations
from aegis.control.action_registry import validate_proposal

class RestrictedRunner:
    def execute(self, proposal: dict[str, object]) -> dict[str, object]:
        target = proposal.get("target", {})
        action = validate_proposal(str(proposal["action_key"]), target, proposal.get("parameters", {}))
        return {"state": "SUCCEEDED", "action": action.action_id, "target": target}
