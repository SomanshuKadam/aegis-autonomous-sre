from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo import ASCENDING
from pymongo.collection import Collection

from aegis.config import Settings, get_settings
from aegis.control.models import IncidentState
from aegis.control.state_machine import transition
from aegis.integrations.mongodb import MongoStore
from aegis.types import new_id, utc_now


def _document(value: dict[str, Any] | None) -> dict[str, object]:
    if value is None:
        raise KeyError("incident was not found")
    value.pop("_id", None)
    return value


class IncidentStore:
    """Mongo-backed incident aggregate with idempotent commands and append-only records."""

    def __init__(self, settings: Settings | None = None) -> None:
        store = MongoStore(settings or get_settings())
        self.db = store.db
        store.bootstrap()
        self.incidents: Collection = self.db["incidents"]
        self.commands: Collection = self.db["incident_commands"]
        self.timeline: Collection = self.db["timeline"]
        self.alerts: Collection = self.db["alerts"]
        self.incidents.create_index("dedup_key", unique=True)
        self.commands.create_index([("incident_id", ASCENDING), ("command_id", ASCENDING)], unique=True)
        self.timeline.create_index([("incident_id", ASCENDING), ("sequence", ASCENDING)], unique=True)

    @property
    def items(self) -> dict[str, dict[str, object]]:
        return {str(record["incident_id"]): _document(record) for record in self.incidents.find({})}

    def create(self, category: str, dedup_key: str, *, source: str = "manual", fingerprint: str = "", target: dict[str, object] | None = None, trace_id: str | None = None) -> dict[str, object]:
        now = utc_now()
        existing = self.incidents.find_one({"dedup_key": dedup_key, "state": {"$nin": [state.value for state in {IncidentState.RESOLVED, IncidentState.FAILED, IncidentState.ROLLED_BACK, IncidentState.ESCALATED, IncidentState.BLOCKED}]}})
        if existing is not None:
            self.incidents.update_one({"incident_id": existing["incident_id"]}, {"$inc": {"alert_count": 1}, "$set": {"updated_at": now}})
            self.alerts.insert_one({"alert_event_id": new_id(), "incident_id": existing["incident_id"], "source": source, "fingerprint": fingerprint, "target": target or {}, "trace_id": trace_id, "received_at": now, "deduplicated": True})
            self._append(str(existing["incident_id"]), str(existing["state"]), "alert", "deduplicated", "Duplicate alert delivery merged into active incident", now)
            return _document(self.incidents.find_one({"incident_id": existing["incident_id"]}))
        incident = {
            "incident_id": new_id(),
            "dedup_key": dedup_key,
            "category": category,
            "state": IncidentState.DETECTED.value,
            "target": target or {},
            "source": source,
            "fingerprint": fingerprint,
            "trace_id": trace_id,
            "evidence_version": 1,
            "timeline_sequence": 0,
            "created_at": now,
            "updated_at": now,
            "version": 1,
            "alert_count": 1,
        }
        try:
            self.incidents.insert_one(incident)
        except Exception:
            existing = self.incidents.find_one({"dedup_key": dedup_key})
            if existing is not None:
                return _document(existing)
            raise
        self.alerts.insert_one({"alert_event_id": new_id(), "incident_id": incident["incident_id"], "source": source, "fingerprint": fingerprint, "target": target or {}, "trace_id": trace_id, "received_at": now})
        self._append(incident["incident_id"], IncidentState.DETECTED.value, "alert", "accepted", "Alert accepted and incident created", now)
        return _document(incident)

    def get(self, incident_id: str) -> dict[str, object]:
        return _document(self.incidents.find_one({"incident_id": incident_id}))

    def list(self, *, cursor: int = 0, limit: int = 50) -> list[dict[str, object]]:
        records = self.incidents.find({}).sort("updated_at", -1).skip(cursor).limit(min(limit, 100))
        return [_document(record) for record in records]

    def records(self, incident_id: str) -> dict[str, list[dict[str, object]]]:
        return {
            "timeline": [_document(record) for record in self.timeline.find({"incident_id": incident_id}).sort("sequence", ASCENDING)],
            "evidence": [_document(record) for record in self.db["evidence"].find({"incident_id": incident_id})],
            "hypotheses": [_document(record) for record in self.db["hypotheses"].find({"incident_id": incident_id})],
            "proposals": [_document(record) for record in self.db["proposals"].find({"incident_id": incident_id})],
            "policy_decisions": [_document(record) for record in self.db["policy_decisions"].find({"incident_id": incident_id})],
            "approvals": [_document(record) for record in self.db["approvals"].find({"incident_id": incident_id})],
            "executions": [_document(record) for record in self.db["executions"].find({"incident_id": incident_id})],
            "verifications": [_document(record) for record in self.db["verifications"].find({"incident_id": incident_id})],
            "rollbacks": [_document(record) for record in self.db["rollbacks"].find({"incident_id": incident_id})],
            "notifications": [_document(record) for record in self.db["notifications"].find({"incident_id": incident_id})],
        }

    def advance(self, incident_id: str, target: str, command_id: str, *, actor: str = "orchestrator", reason: str = "") -> dict[str, object]:
        command = self.commands.find_one({"incident_id": incident_id, "command_id": command_id})
        if command is not None:
            return {"incident": self.get(incident_id), "disposition": str(command["disposition"]), "command_id": command_id}
        incident = self.get(incident_id)
        if incident["state"] == target:
            disposition = "already-at-target"
        else:
            next_state = transition(IncidentState(str(incident["state"])), IncidentState(target)).value
            now = utc_now()
            result = self.incidents.find_one_and_update(
                {"incident_id": incident_id, "state": incident["state"]},
                {"$set": {"state": next_state, "updated_at": now}, "$inc": {"timeline_sequence": 1, "version": 1}},
                return_document=True,
            )
            if result is None:
                raise ValueError("incident was updated concurrently; retry with a new command")
            incident = _document(result)
            self._append(incident_id, next_state, "lifecycle", "advanced", reason or f"{actor} advanced incident", now, actor)
            disposition = "advanced"
        self.commands.insert_one({"incident_id": incident_id, "command_id": command_id, "target_state": target, "disposition": disposition, "actor": actor, "occurred_at": utc_now()})
        return {"incident": incident, "disposition": disposition, "command_id": command_id}

    def record(self, collection: str, incident_id: str, payload: dict[str, object]) -> dict[str, object]:
        document = {**payload, "incident_id": incident_id, "occurred_at": utc_now()}
        self.db[collection].insert_one(document)
        timeline_labels = {
            "evidence": ("evidence", "collected", "Current evidence snapshot collected"),
            "hypotheses": ("investigation", "evaluated", "Root-cause hypothesis evaluated"),
            "proposals": ("planning", "proposed", "Registered remediation action proposed"),
            "policy_decisions": ("policy", str(payload.get("outcome", "evaluated")).lower(), "Deterministic policy decision recorded"),
            "approvals": ("approval", str(payload.get("state", "recorded")).lower(), "Exact approval state recorded"),
            "executions": ("execution", str(payload.get("state", "recorded")).lower(), "Restricted runner execution recorded"),
            "verifications": ("verification", str(payload.get("outcome", "recorded")).lower(), "Post-action verification recorded"),
            "rollbacks": ("rollback", str(payload.get("outcome", "recorded")).lower(), "Compensation or escalation recorded"),
            "notifications": ("notification", str(payload.get("state", "recorded")).lower(), "External notification delivery recorded"),
            "agent_runs": ("agent", str(payload.get("outcome", "recorded")).lower(), "Bounded investigation agent result recorded"),
        }
        if collection in timeline_labels:
            stage, outcome, summary = timeline_labels[collection]
            self._append(incident_id, stage, collection, outcome, summary, document["occurred_at"])
        return _document(document)

    def _append(self, incident_id: str, stage: str, event_type: str, outcome: str, summary: str, occurred_at: datetime, actor: str = "system") -> None:
        sequence = self.db["timeline_counters"].find_one_and_update(
            {"incident_id": incident_id},
            {"$inc": {"sequence": 1}, "$setOnInsert": {"incident_id": incident_id}},
            upsert=True,
            return_document=True,
        )["sequence"]
        self.timeline.insert_one({"event_id": new_id(), "incident_id": incident_id, "sequence": sequence, "occurred_at": occurred_at, "stage": stage, "type": event_type, "outcome": outcome, "summary": summary, "actor": actor})
