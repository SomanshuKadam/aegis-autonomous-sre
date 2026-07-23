from fastapi.testclient import TestClient
from aegis.api.app import create_app

def test_operations_summary_and_paginated_incident_list() -> None:
    client = TestClient(create_app())
    assert client.get("/api/v1/operations/overview").status_code == 200
    response = client.get("/api/v1/operations/incidents")
    assert response.status_code == 200 and "ETag" in response.headers
