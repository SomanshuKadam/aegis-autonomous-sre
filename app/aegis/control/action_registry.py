from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class ActionDefinition:
    action_id: str
    version: int
    risk: str
    target_type: str
    required_evidence: tuple[str, ...]
    timeout_seconds: int
    allowed_parameters: tuple[str, ...] = ()
    verification_profile: str = "exact_state"
    rollback_action: str | None = None
    maximum_attempts: int = 1

ACTIONS = {
    "mongo.create_search_index@1": ActionDefinition("mongo.create_search_index", 1, "LOW", "mongodb_collection", ("catalog_search",), 60, (), "catalog_search", None),
    "inventory.restore_capacity@1": ActionDefinition("inventory.restore_capacity", 1, "MEDIUM", "inventory_dependency", ("inventory_health",), 60, ("desired",), "inventory", "inventory.restore_capacity@1"),
    "worker.set_capacity@1": ActionDefinition("worker.set_capacity", 1, "LOW", "order_worker", ("queue_backlog",), 60, ("desired",), "backlog", "worker.set_capacity@1"),
}

def resolve(key: str) -> ActionDefinition:
    if key not in ACTIONS: raise ValueError("action is not registered")
    return ACTIONS[key]

def validate_proposal(key: str, target: dict[str, object], parameters: dict[str, object]) -> ActionDefinition:
    action = resolve(key)
    if target.get("type") != action.target_type: raise ValueError("action target is not authorized")
    if set(parameters) - set(action.allowed_parameters): raise ValueError("action contains unexpected parameters")
    if set(action.allowed_parameters) - set(parameters): raise ValueError("action is missing required parameters")
    return action
