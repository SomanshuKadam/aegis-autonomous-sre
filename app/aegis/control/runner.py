from __future__ import annotations
from aegis.control.action_registry import resolve

class RestrictedRunner:
    def execute(self, proposal: dict[str, object]) -> dict[str, object]:
        action = resolve(str(proposal["action_key"])); target = proposal.get("target", {})
        if target.get("type") != action.target_type: raise ValueError("action target is not authorized")
        return {"state": "SUCCEEDED", "action": action.action_id, "target": target}
