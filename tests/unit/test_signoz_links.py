from aegis.integrations.signoz_links import trace_link

def test_signoz_links_reject_invalid_context_and_unknown_service() -> None:
    assert trace_link("bad", "aegis-api")["url"] is None
    assert trace_link("a" * 32, "unknown")["url"] is None
    assert "/trace/" in str(trace_link("a" * 32, "aegis-api")["url"])
