import pytest
from aegis.control.actions.mongodb_index import create_search_index
from aegis.control.verifiers.catalog_search import verify_catalog_search

def test_catalog_action_requires_exact_target_and_fresh_evidence() -> None:
    target = {"database": "mydatabase", "collection": "products", "field": "search_text"}
    assert create_search_index(target, {"missing_index": True, "fresh_search_failure": True})["state"] == "SUCCEEDED"
    with pytest.raises(ValueError): create_search_index(target, {"missing_index": True})
    assert verify_catalog_search(True, 1999, True)["outcome"] == "VERIFIED"
