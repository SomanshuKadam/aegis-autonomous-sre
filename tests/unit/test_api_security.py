from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from aegis.api.security import require_orchestrator


def test_orchestrator_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("AEGIS_ORCHESTRATOR_TOKEN", "test-token")
    from aegis.config import get_settings
    get_settings.cache_clear()
    app = FastAPI()
    @app.get("/protected", dependencies=[Depends(require_orchestrator)])
    def protected():
        return {"ok": True}
    client = TestClient(app)
    assert client.get("/protected").status_code == 401
    assert client.get("/protected", headers={"Authorization": "Bearer test-token"}).status_code == 200
