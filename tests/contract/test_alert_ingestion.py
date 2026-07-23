from fastapi.testclient import TestClient
from aegis.api.app import create_app
from aegis.config import get_settings

def test_alert_ingestion_is_token_protected_and_deduplicated(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_ORCHESTRATOR_TOKEN", "alerts-token"); get_settings.cache_clear()
    client = TestClient(create_app()); payload = {"source": "signoz", "fingerprint": "p95-1", "category": "catalog_search", "target": {"collection": "products"}}
    assert client.post("/api/v1/orchestration/alerts", json=payload).status_code == 401
    headers = {"Authorization": "Bearer alerts-token"}
    first = client.post("/api/v1/orchestration/alerts", json=payload, headers=headers).json()
    second = client.post("/api/v1/orchestration/alerts", json=payload, headers=headers).json()
    assert second["incident_id"] == first["incident_id"]
