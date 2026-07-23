from __future__ import annotations
from aegis.types import canonical_hash
def dedup_key(source: str, fingerprint: str, category: str, target: dict[str, object]) -> str: return canonical_hash({"source": source, "fingerprint": fingerprint, "category": category, "target": target})
def operation_key(incident_id: str, action_id: str, parameters: dict[str, object], evidence_version: int) -> str: return canonical_hash({"incident_id": incident_id, "action_id": action_id, "parameters": parameters, "evidence_version": evidence_version})
