from __future__ import annotations

from pymongo import ReturnDocument

from aegis.integrations.mongodb import MongoStore


class ServiceState:
    def __init__(self, service: str, defaults: dict[str, object]) -> None:
        from aegis.config import get_settings
        self.service = service
        self.defaults = defaults
        self.db = MongoStore(get_settings()).db
        self.collection = self.db["service_state"]
        self.collection.update_one({"service": service}, {"$setOnInsert": {"service": service, **defaults}}, upsert=True)

    def read(self) -> dict[str, object]:
        value = self.collection.find_one({"service": self.service})
        value.pop("_id", None)
        return value

    def update_capacity(self, desired: int) -> dict[str, object]:
        current = self.read()
        value = self.collection.find_one_and_update({"service": self.service}, {"$set": {"previous": current["desired"], "desired": desired}}, return_document=ReturnDocument.AFTER)
        value.pop("_id", None)
        return value
