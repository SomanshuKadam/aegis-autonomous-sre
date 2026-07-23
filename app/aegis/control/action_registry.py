from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class ActionDefinition:
    action_id: str; version: int; risk: str; target_type: str; required_evidence: tuple[str, ...]; timeout_seconds: int

ACTIONS = {
    "mongo.create_search_index@1": ActionDefinition("mongo.create_search_index", 1, "LOW", "mongodb_collection", ("catalog_search",), 60),
    "inventory.restore_capacity@1": ActionDefinition("inventory.restore_capacity", 1, "MEDIUM", "inventory_dependency", ("inventory_health",), 60),
    "worker.increase_capacity@1": ActionDefinition("worker.increase_capacity", 1, "MEDIUM", "order_worker", ("queue_backlog",), 60),
}

def resolve(key: str) -> ActionDefinition:
    if key not in ACTIONS: raise ValueError("action is not registered")
    return ACTIONS[key]
