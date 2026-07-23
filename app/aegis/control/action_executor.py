from __future__ import annotations

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError
import httpx

from aegis.config import Settings, get_settings
from aegis.control.action_registry import validate_proposal


class ActionExecutor:
    """The only component permitted to apply registered mutations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        from pymongo import MongoClient
        self.db = MongoClient(self.settings.mongodb_uri.get_secret_value(), serverSelectionTimeoutMS=5000)[self.settings.mongo_database]
        self.executions = self.db["runner_executions"]
        self.executions.create_index("idempotency_key", unique=True)

    def execute(self, proposal: dict[str, object]) -> dict[str, object]:
        action = validate_proposal(str(proposal["action_key"]), dict(proposal.get("target", {})), dict(proposal.get("parameters", {})))
        key = str(proposal.get("idempotency_key") or proposal.get("proposal_id"))
        if not key:
            raise ValueError("registered actions require a proposal idempotency key")
        claimed = {"idempotency_key": key, "proposal_id": proposal.get("proposal_id"), "action_key": proposal["action_key"], "state": "CLAIMED"}
        try:
            self.executions.insert_one(claimed)
        except DuplicateKeyError:
            existing = self.executions.find_one({"idempotency_key": key}) or {}
            existing.pop("_id", None)
            return {**existing, "state": "DUPLICATE"}
        self.executions.update_one({"idempotency_key": key}, {"$set": {"state": "RUNNING"}})
        try:
            if action.action_id == "mongo.create_search_index":
                result = self._create_catalog_index(dict(proposal["target"]))
            elif action.action_id == "inventory.restore_capacity":
                result = self._set_service_capacity(self.settings.inventory_url, dict(proposal["target"]), int(dict(proposal["parameters"])["desired"]), "inventory_dependency")
            elif action.action_id == "worker.set_capacity":
                result = self._set_service_capacity(self.settings.worker_url, dict(proposal["target"]), int(dict(proposal["parameters"])["desired"]), "order_worker")
            else:
                raise ValueError(f"registered action handler is unavailable for {action.action_id}")
        except httpx.TimeoutException as exc:
            self.executions.update_one({"idempotency_key": key}, {"$set": {"state": "TIMED_OUT", "error": str(exc)}})
            return {"state": "TIMED_OUT", "idempotency_key": key, "safe_summary": "registered action timed out"}
        except Exception as exc:
            self.executions.update_one({"idempotency_key": key}, {"$set": {"state": "FAILED", "error": str(exc)}})
            return {"state": "FAILED", "idempotency_key": key, "safe_summary": "registered action failed"}
        final_state = str(result.get("state", "SUCCEEDED"))
        self.executions.update_one({"idempotency_key": key}, {"$set": {"state": final_state, "result": result}})
        return {"idempotency_key": key, **result}

    def rollback(self, action_key: str, target: dict[str, object], previous_state: dict[str, object]) -> dict[str, object]:
        action = validate_proposal(action_key, target, {"desired": int(previous_state["desired"])})
        if action.action_id == "inventory.restore_capacity":
            return self._set_service_capacity(self.settings.inventory_url, target, int(previous_state["desired"]), "inventory_dependency", rollback=True)
        if action.action_id == "worker.set_capacity":
            return self._set_service_capacity(self.settings.worker_url, target, int(previous_state["desired"]), "order_worker", rollback=True)
        raise ValueError("the registered action has no compensating mutation")

    def _set_service_capacity(self, base_url: str, target: dict[str, object], desired: int, expected_type: str, rollback: bool = False) -> dict[str, object]:
        if target.get("type") != expected_type:
            raise ValueError("action target does not match the registered service")
        before = httpx.get(f"{base_url.rstrip('/')}/health", timeout=10)
        before.raise_for_status()
        previous = {"desired": int(before.json()["capacity"])}
        if previous["desired"] == desired:
            return {"state": "NOOP", "action": "service.set_capacity", "target": target, "previous_state": previous, "desired": desired}
        headers = {"Authorization": f"Bearer {self.settings.runner_token.get_secret_value()}"}
        if rollback:
            headers["X-Aegis-Rollback"] = "true"
        response = httpx.post(f"{base_url.rstrip('/')}/control/capacity", params={"desired": desired}, headers=headers, timeout=60)
        response.raise_for_status()
        return {"action": "service.set_capacity", "target": target, "previous_state": previous, **response.json()}

    def _create_catalog_index(self, target: dict[str, object]) -> dict[str, object]:
        expected = {"type": "mongodb_collection", "database": self.settings.mongo_database, "collection": "products", "field": "search_text"}
        if target != expected:
            raise ValueError("catalog action target does not exactly match the registered catalog collection")
        collection = self.db["products"]
        if collection.estimated_document_count() == 0:
            collection.insert_many([
                {"product_id": "product-001", "sku": "sku-001", "name": "Aegis Notebook", "search_text": "aegis notebook reliability", "price_minor": 1299},
                {"product_id": "product-002", "sku": "sku-002", "name": "Signal Mug", "search_text": "signal mug observability", "price_minor": 899},
            ])
        names = {item["name"] for item in collection.list_indexes()}
        if "search_text_1" in names:
            return {"state": "NOOP", "action": "mongo.create_search_index", "index": "search_text_1", "target": target}
        index = collection.create_index([("search_text", ASCENDING)], name="search_text_1")
        return {"state": "SUCCEEDED", "action": "mongo.create_search_index", "index": index, "target": target}
