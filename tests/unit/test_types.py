import pytest
from aegis.types import CorrelationIds, canonical_hash

def test_correlation_rejects_invalid_trace_and_span_identifiers() -> None:
    with pytest.raises(ValueError): CorrelationIds(trace_id="A" * 32)
    with pytest.raises(ValueError): CorrelationIds(span_id="a" * 15)
    assert canonical_hash({"b": 1, "a": 2}) == canonical_hash({"a": 2, "b": 1})
