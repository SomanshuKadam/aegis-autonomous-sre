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
        legacy_key = [("incident_id", ASCENDING), ("proposal_hash", ASCENDING)]
        for name, definition in self.collection.index_information().items():
            if name != "_id_" and definition.get("unique") and list(definition.get("key", [])) == legacy_key:
                self.collection.drop_index(name)
        self.collection.create_index("approval_id", unique=True)
        self.collection.create_index(
            [("incident_id", ASCENDING), ("proposal_hash", ASCENDING), ("attempt", ASCENDING)],
            unique=True,
        )
        self.collection.create_index([("state", ASCENDING), ("expires_at", ASCENDING)])

    def request(self, incident_id: str, proposal: dict[str, object], ttl_minutes: int = 15) -> dict[str, object]:
        proposal_hash = self._proposal_hash(proposal)
        now = utc_now()
        existing = self.collection.find_one(
            {
                "incident_id": incident_id,
                "proposal_hash": proposal_hash,
                "state": "PENDING",
                "expires_at": {"$gte": now},
            },
            sort=[("attempt", -1), ("created_at", -1)],
        )
        if existing:
            existing.pop("_id", None)
            return existing
        latest = self.collection.find_one(
            {"incident_id": incident_id, "proposal_hash": proposal_hash},
            sort=[("attempt", -1), ("created_at", -1)],
        )
        attempt = int(latest.get("attempt", 1) if latest else 0) + 1
        record = {
            "approval_id": new_id(),
            "incident_id": incident_id,
            "proposal_id": proposal["proposal_id"],
            "proposal_hash": proposal_hash,
            "evidence_version": proposal["evidence_version"],
            "attempt": attempt,
            "state": "PENDING",
            "expires_at": now + timedelta(minutes=ttl_minutes),
            "created_at": now,
        }
        self.collection.insert_one(record)
        self.incidents._append(incident_id, "approval", "approval", "pending", "Exact approval request recorded", record["created_at"])
        record.pop("_id", None)
        return record

    def reconcile_expired(self) -> list[dict[str, str]]:
        now = utc_now()
        candidates = list(self.collection.find({"state": "PENDING", "expires_at": {"$lte": now}}))
        for candidate in candidates:
            expired = self.collection.find_one_and_update(
                {
                    "approval_id": candidate["approval_id"],
                    "state": "PENDING",
                    "expires_at": {"$lte": now},
                },
                {"$set": {"state": "EXPIRED", "expired_at": now}},
                return_document=True,
            )
            if expired is not None:
                self.incidents._append(
                    str(expired["incident_id"]),
                    "approval",
                    "approval",
                    "expired",
                    "Approval window expired without an operator decision",
                    now,
                    "reconciler",
                )
        events: list[dict[str, str]] = []
        for approval in self.collection.find({"state": "EXPIRED"}):
            incident_id = str(approval["incident_id"])
            approval_id = str(approval["approval_id"])
            occurred_at = approval.get("expired_at") or now
            if self.incidents.escalate_expired_approval(incident_id, approval_id, occurred_at):
                events.append(
                    {
                        "operation": "EXPIRED",
                        "incident_id": incident_id,
                        "approval_id": approval_id,
                    }
                )
        return events

    def consume(self, incident_id: str, approval_id: str, proposal: dict[str, object], approver: str, decision: str) -> dict[str, object]:
        record = self.collection.find_one({"approval_id": approval_id, "incident_id": incident_id})
        expires_at = record["expires_at"] if record else utc_now()
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=utc_now().tzinfo)
        if (
            record is None
            or record["state"] != "PENDING"
            or expires_at < utc_now()
            or record["proposal_id"] != proposal["proposal_id"]
            or record["proposal_hash"] != self._proposal_hash(proposal)
            or record["evidence_version"] != proposal["evidence_version"]
        ):
            raise ValueError("approval is invalid, expired, already used, or does not match the proposal")
        state = "APPROVED" if decision == "APPROVED" else "REJECTED"
        record = self.collection.find_one_and_update(
            {"approval_id": approval_id, "incident_id": incident_id, "state": "PENDING", "proposal_hash": self._proposal_hash(proposal), "expires_at": {"$gte": utc_now()}},
            {"$set": {"state": state, "approver": approver, "decided_at": utc_now()}},
            return_document=True,
        )
        if record is None:
            raise ValueError("approval was consumed concurrently")
        self.incidents._append(incident_id, "approval", "approval", state.lower(), "Exact approval decision recorded", record["decided_at"])
        record.pop("_id", None)
        return record

    @staticmethod
    def _proposal_hash(proposal: dict[str, object]) -> str:
        normalized = dict(proposal)
        normalized.pop("occurred_at", None)
        normalized.pop("created_at", None)
        return canonical_hash(normalized)
