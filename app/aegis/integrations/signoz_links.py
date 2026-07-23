from __future__ import annotations
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from aegis.types import CorrelationIds

ALLOWED_SERVICES = {"aegis-api", "aegis-inventory", "aegis-worker", "aegis-workload"}

def trace_link(trace_id: str, service: str, base_url: str = "http://localhost:3301") -> dict[str, str | None]:
    try: CorrelationIds(trace_id=trace_id)
    except ValueError: return {"url": None, "reason": "invalid trace correlation"}
    if service not in ALLOWED_SERVICES: return {"url": None, "reason": "service is not allowlisted"}
    end = datetime.now(timezone.utc); start = end - timedelta(hours=1)
    return {"url": f"{base_url}/trace/{trace_id}?{urlencode({'service': service, 'start': start.isoformat(), 'end': end.isoformat()})}", "reason": None}

def context_links(trace_id: str, service: str, base_url: str = "http://localhost:3301") -> dict[str, dict[str, str | None]]:
    trace = trace_link(trace_id, service, base_url)
    if trace["url"] is None: return {name: {"url": None, "reason": trace["reason"]} for name in ("trace", "logs", "service", "dashboard")}
    return {"trace": trace, "logs": {"url": f"{base_url}/logs?{urlencode({'service': service})}", "reason": None}, "service": {"url": f"{base_url}/services/{service}", "reason": None}, "dashboard": {"url": f"{base_url}/dashboard?{urlencode({'service': service})}", "reason": None}}
