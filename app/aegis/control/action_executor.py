from __future__ import annotations

from pymongo import ASCENDING

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
        raise ValueError(f"registered action handler is unavailable for {action.action_id}")

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
