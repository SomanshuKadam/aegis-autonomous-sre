from fastapi.testclient import TestClient

from aegis.api.app import create_app


def test_catalog_order_and_idempotency() -> None:
    client = TestClient(create_app())
    assert client.get("/api/v1/products").json()["items"]
    headers = {"Idempotency-Key": "order-001"}
    first = client.post("/api/v1/orders", json={"sku": "sku-001", "quantity": 2}, headers=headers)
    second = client.post("/api/v1/orders", json={"sku": "sku-001", "quantity": 2}, headers=headers)
    assert first.status_code == 201 and second.json()["order_id"] == first.json()["order_id"]
