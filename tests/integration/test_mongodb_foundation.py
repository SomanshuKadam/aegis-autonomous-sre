from unittest.mock import MagicMock
from aegis.config import Settings
from aegis.integrations.mongodb import MongoStore

def test_bootstrap_registers_unique_incident_and_timeline_indexes(monkeypatch) -> None:
    client = MagicMock(); monkeypatch.setattr("aegis.integrations.mongodb.MongoClient", lambda *args, **kwargs: client)
    store = MongoStore(Settings(MONGODB_URI="mongodb://example")); store.bootstrap()
    assert store.db.incidents.create_index.called and store.db.timeline.create_index.called
