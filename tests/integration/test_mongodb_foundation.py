from unittest.mock import MagicMock
from aegis.config import Settings
from aegis.integrations.mongodb import MongoStore
from aegis.integrations.repositories import Repository

def test_bootstrap_registers_unique_incident_and_timeline_indexes(monkeypatch) -> None:
    client = MagicMock(); monkeypatch.setattr("aegis.integrations.mongodb.MongoClient", lambda *args, **kwargs: client)
    store = MongoStore(Settings(MONGODB_URI="mongodb://example")); store.bootstrap()
    assert store.db.incidents.create_index.called and store.db.timeline.create_index.called

def test_repository_requests_atomic_monotonic_sequence() -> None:
    collection = MagicMock(); collection.find_one_and_update.return_value = {"sequence": 3}
    assert Repository(collection).next_sequence("incident-1") == 3
    update = collection.find_one_and_update.call_args.args[1]
    assert update["$inc"] == {"sequence": 1}
