from __future__ import annotations

def create_search_index(target: dict[str, str], evidence: dict[str, object]) -> dict[str, object]:
    if target != {"database": "mydatabase", "collection": "products", "field": "search_text"}: raise ValueError("catalog index target is not authorized")
    if not evidence.get("missing_index") or not evidence.get("fresh_search_failure"): raise ValueError("catalog index evidence predicates are not satisfied")
    operation = f"{target['collection']}_{target['field']}_1"
    return {"state": "SUCCEEDED", "index": operation, "idempotency_key": operation, "created": not bool(evidence.get("index_present"))}
