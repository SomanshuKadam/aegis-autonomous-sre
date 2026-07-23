from __future__ import annotations
from collections.abc import Mapping
from pymongo import ReturnDocument
from pymongo.collection import Collection

class Repository:
    def __init__(self, collection: Collection): self.collection = collection
    def insert_once(self, document: Mapping[str, object], key: str) -> dict[str, object]:
        self.collection.update_one({key: document[key]}, {"$setOnInsert": dict(document)}, upsert=True)
        return self.collection.find_one({key: document[key]}) or {}
    def append(self, document: Mapping[str, object]) -> None: self.collection.insert_one(dict(document))
    def claim(self, query: Mapping[str, object], update: Mapping[str, object]) -> dict[str, object] | None:
        return self.collection.find_one_and_update(dict(query), dict(update), return_document=ReturnDocument.AFTER)
