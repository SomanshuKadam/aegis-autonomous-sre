from __future__ import annotations

from pymongo import ASCENDING
import httpx

from aegis.config import Settings, get_settings
from aegis.control.action_registry import validate_proposal


class ActionExecutor:
    """The only component permitted to apply registered mutations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        from pymongo import MongoClient
        self.db = MongoClient(self.settings.mongodb_uri.get_secret_value(), serverSelectionTimeoutMS=5000)[self.settings.mongo_database]

    def execute(self, proposal: dict[str, object]) -> dict[str, object]:
        action = validate_proposal(str(proposal["action_key"]), dict(proposal.get("target", {})), dict(proposal.get("parameters", {})))
        if action.action_id == "mongo.create_search_index":
            return self._create_catalog_index(dict(proposal["target"]))
        if action.action_id == "inventory.restore_capacity":
            return self._set_service_capacity(self.settings.inventory_url, dict(proposal["target"]), int(dict(proposal["parameters"])["desired"]), "inventory_dependency")
        if action.action_id == "worker.set_capacity":
            return self._set_service_capacity(self.settings.worker_url, dict(proposal["target"]), int(dict(proposal["parameters"])["desired"]), "order_worker")
        raise ValueError(f"registered action handler is unavailable for {action.action_id}")

    def _set_service_capacity(self, base_url: str, target: dict[str, object], desired: int, expected_type: str) -> dict[str, object]:
        if target.get("type") != expected_type:
            raise ValueError("action target does not match the registered service")
        response = httpx.post(f"{base_url.rstrip('/')}/control/capacity", params={"desired": desired}, headers={"Authorization": f"Bearer {self.settings.runner_token.get_secret_value()}"}, timeout=60)
        response.raise_for_status()
        return {"action": "service.set_capacity", "target": target, **response.json()}

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
