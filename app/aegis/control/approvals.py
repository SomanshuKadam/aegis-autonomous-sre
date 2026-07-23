from __future__ import annotations

from datetime import timedelta

from pymongo import ASCENDING

from aegis.control.incidents import IncidentStore
from aegis.types import canonical_hash, new_id, utc_now


class ApprovalStore:
    """Durable, proposal-bound, single-use approval commands."""

    def __init__(self, incidents: IncidentStore) -> None:
        self.incidents = incidents
        self.collection = incidents.db["approvals"]
        self.collection.create_index([("incident_id", ASCENDING), ("proposal_hash", ASCENDING)], unique=True)

    def request(self, incident_id: str, proposal: dict[str, object], ttl_minutes: int = 15) -> dict[str, object]:
        proposal_hash = self._proposal_hash(proposal)
        existing = self.collection.find_one({"incident_id": incident_id, "proposal_hash": proposal_hash})
        if existing:
            existing.pop("_id", None)
            return existing
        record = {"approval_id": new_id(), "incident_id": incident_id, "proposal_id": proposal["proposal_id"], "proposal_hash": proposal_hash, "evidence_version": proposal["evidence_version"], "state": "PENDING", "expires_at": utc_now() + timedelta(minutes=ttl_minutes), "created_at": utc_now()}
        self.collection.insert_one(record)
        self.incidents._append(incident_id, "approval", "approval", "pending", "Exact approval request recorded", record["created_at"])
        record.pop("_id", None)
        return record

    def consume(self, incident_id: str, approval_id: str, proposal: dict[str, object], approver: str, decision: str) -> dict[str, object]:
        record = self.collection.find_one({"approval_id": approval_id, "incident_id": incident_id})
        expires_at = record["expires_at"] if record else utc_now()
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=utc_now().tzinfo)
        if record is None or record["state"] != "PENDING" or expires_at < utc_now() or record["proposal_id"] != proposal["proposal_id"]:
            raise ValueError("approval is invalid, expired, already used, or does not match the proposal")
        state = "APPROVED" if decision == "APPROVED" else "REJECTED"
        self.collection.update_one({"approval_id": approval_id, "state": "PENDING"}, {"$set": {"state": state, "approver": approver, "decided_at": utc_now()}})
        record = self.collection.find_one({"approval_id": approval_id})
        self.incidents._append(incident_id, "approval", "approval", state.lower(), "Exact approval decision recorded", record["decided_at"])
        record.pop("_id", None)
        return record

    @staticmethod
    def _proposal_hash(proposal: dict[str, object]) -> str:
        normalized = dict(proposal)
        normalized.pop("occurred_at", None)
        return canonical_hash(normalized)
