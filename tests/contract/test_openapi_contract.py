from pathlib import Path
import yaml
from fastapi.testclient import TestClient
from aegis.api.app import create_app


def test_health_and_readiness_return_stable_envelopes() -> None:
    client = TestClient(create_app())
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/readiness").json()["ready"] is True


def test_openapi_contract_parses_and_all_local_references_resolve() -> None:
    root = Path("/app/specs/001-application-reliability-platform") if Path("/app/specs").exists() else Path("specs/001-application-reliability-platform")
    contract = yaml.safe_load((root / "contracts/http-api.openapi.yaml").read_text(encoding="utf-8"))
    assert contract["openapi"] == "3.1.0"
    components = contract["components"]
    def walk(value):
        if isinstance(value, dict):
            if "$ref" in value and value["$ref"].startswith("#/components/"):
                _, _, group, name = value["$ref"].split("/")
                assert name in components[group]
            for child in value.values(): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(contract)
