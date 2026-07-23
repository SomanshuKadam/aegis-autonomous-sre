from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel


class IncidentState(StrEnum):
    DETECTED="DETECTED"; VALIDATING="VALIDATING"; ENRICHING="ENRICHING"; INVESTIGATING="INVESTIGATING"; ROOT_CAUSE_IDENTIFIED="ROOT_CAUSE_IDENTIFIED"; ACTION_PROPOSED="ACTION_PROPOSED"; POLICY_CHECKED="POLICY_CHECKED"; BLOCKED="BLOCKED"; APPROVAL_REQUIRED="APPROVAL_REQUIRED"; AUTO_APPROVED="AUTO_APPROVED"; EXECUTING="EXECUTING"; VERIFYING="VERIFYING"; RESOLVED="RESOLVED"; FAILED="FAILED"; ROLLED_BACK="ROLLED_BACK"; ESCALATED="ESCALATED"

class Incident(BaseModel): incident_id: str; dedup_key: str; category: str; state: IncidentState = IncidentState.DETECTED; evidence_version: int = 1; timeline_sequence: int = 0; created_at: datetime; updated_at: datetime
class AlertEvent(BaseModel): alert_event_id: str; incident_id: str; source: str; fingerprint: str; received_at: datetime
class TimelineEvent(BaseModel): event_id: str; incident_id: str; sequence: int; occurred_at: datetime; stage: str; type: str; outcome: str; summary: str
class EvidenceRecord(BaseModel): evidence_id: str; incident_id: str; type: str; source: str; freshness: str; observation: str; reference: dict[str, str] = {}
class Hypothesis(BaseModel): hypothesis_id: str; incident_id: str; statement: str; disposition: str; evidence_ids: list[str] = []
class ActionProposal(BaseModel): proposal_id: str; incident_id: str; action_id: str; action_version: int; target: dict[str, str]; parameters: dict[str, object]; evidence_version: int
class PolicyDecision(BaseModel): policy_decision_id: str; proposal_id: str; outcome: str; reason_codes: list[str] = []
class Approval(BaseModel): approval_id: str; proposal_id: str; decision: str; expires_at: datetime
class Execution(BaseModel): execution_id: str; proposal_id: str; state: str; attempt_number: int
class Verification(BaseModel): verification_id: str; execution_id: str; outcome: str
class Rollback(BaseModel): rollback_id: str; execution_id: str; outcome: str
class Notification(BaseModel): notification_id: str; incident_id: str; state: str
