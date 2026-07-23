from fastapi.testclient import TestClient
from aegis.api.app import create_app
from aegis.config import get_settings

def test_replay_endpoint_requires_operator_token(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_OPERATOR_TOKEN", "replay-token"); get_settings.cache_clear()
    client = TestClient(create_app())
    assert client.get("/api/v1/evaluation/replays/catalog-valid").status_code == 401
    response = client.get("/api/v1/evaluation/replays/catalog-valid", headers={"Authorization": "Bearer replay-token"})
    assert response.status_code == 200 and response.json()["live_mutations"] == 0
