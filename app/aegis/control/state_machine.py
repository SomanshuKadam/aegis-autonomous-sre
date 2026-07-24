from __future__ import annotations
from .models import IncidentState

TERMINAL = {IncidentState.BLOCKED, IncidentState.RESOLVED, IncidentState.FAILED, IncidentState.ROLLED_BACK, IncidentState.ESCALATED}
ALLOWED: dict[IncidentState, set[IncidentState]] = {
    IncidentState.DETECTED: {IncidentState.VALIDATING, IncidentState.ESCALATED}, IncidentState.VALIDATING: {IncidentState.ENRICHING, IncidentState.BLOCKED, IncidentState.ESCALATED},
    IncidentState.ENRICHING: {IncidentState.INVESTIGATING, IncidentState.BLOCKED, IncidentState.ESCALATED}, IncidentState.INVESTIGATING: {IncidentState.ROOT_CAUSE_IDENTIFIED, IncidentState.BLOCKED, IncidentState.ESCALATED},
    IncidentState.ROOT_CAUSE_IDENTIFIED: {IncidentState.ACTION_PROPOSED, IncidentState.ESCALATED}, IncidentState.ACTION_PROPOSED: {IncidentState.POLICY_CHECKED, IncidentState.ESCALATED}, IncidentState.POLICY_CHECKED: {IncidentState.AUTO_APPROVED, IncidentState.APPROVAL_REQUIRED, IncidentState.BLOCKED, IncidentState.ESCALATED},
    IncidentState.AUTO_APPROVED: {IncidentState.EXECUTING, IncidentState.ESCALATED}, IncidentState.APPROVAL_REQUIRED: {IncidentState.EXECUTING, IncidentState.BLOCKED, IncidentState.ESCALATED}, IncidentState.EXECUTING: {IncidentState.VERIFYING, IncidentState.FAILED, IncidentState.ESCALATED}, IncidentState.VERIFYING: {IncidentState.RESOLVED, IncidentState.FAILED, IncidentState.ROLLED_BACK, IncidentState.ESCALATED},
}
def can_transition(current: IncidentState, target: IncidentState) -> bool: return target in ALLOWED.get(current, set())
def transition(current: IncidentState, target: IncidentState) -> IncidentState:
    if not can_transition(current, target): raise ValueError(f"illegal incident transition {current} -> {target}")
    return target
