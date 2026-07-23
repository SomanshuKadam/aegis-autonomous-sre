from fastapi.testclient import TestClient
from aegis.api.app import create_app

def test_incident_is_deduplicated_and_queryable() -> None:
    client = TestClient(create_app()); payload = {"category": "catalog_search", "dedup_key": "alert-1"}
    first = client.post("/api/v1/orchestration/incidents", json=payload).json()
    assert client.post("/api/v1/orchestration/incidents", json=payload).json()["incident_id"] == first["incident_id"]
    assert client.get(f"/api/v1/orchestration/incidents/{first['incident_id']}").status_code == 200
