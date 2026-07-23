from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from aegis.types import canonical_hash, new_id, utc_now

@dataclass
class ApprovalRecord:
    approval_id: str; proposal_hash: str; expires_at: datetime; consumed: bool = False

class ApprovalStore:
    def __init__(self) -> None: self.records: dict[str, ApprovalRecord] = {}
    def request(self, proposal: dict[str, object], ttl_minutes: int = 15) -> ApprovalRecord:
        record = ApprovalRecord(new_id(), canonical_hash(proposal), utc_now() + timedelta(minutes=ttl_minutes)); self.records[record.approval_id] = record; return record
    def consume(self, approval_id: str, proposal: dict[str, object]) -> ApprovalRecord:
        record = self.records[approval_id]
        if record.consumed or record.expires_at < utc_now() or record.proposal_hash != canonical_hash(proposal): raise ValueError("approval is invalid, expired, or does not match the proposal")
        record.consumed = True; return record
