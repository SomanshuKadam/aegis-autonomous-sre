from fastapi.testclient import TestClient
from aegis.api.app import create_app


def test_health_and_readiness_return_stable_envelopes() -> None:
    client = TestClient(create_app())
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/readiness").json()["ready"] is True
