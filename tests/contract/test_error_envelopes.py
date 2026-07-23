from fastapi.testclient import TestClient
from aegis.api.app import create_app

def test_missing_incident_uses_stable_problem_envelope() -> None:
    response = TestClient(create_app()).get("/api/v1/orchestration/incidents/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
