from __future__ import annotations
from opentelemetry import trace

def record_stage(incident_id: str, stage: str, outcome: str) -> None:
    with trace.get_tracer("aegis.incidents").start_as_current_span("incident.handle") as span:
        span.set_attribute("aegis.incident_id", incident_id)
        span.set_attribute("aegis.stage", stage)
        span.set_attribute("aegis.outcome", outcome)
        span.add_event("incident.stage", {"aegis.stage": stage, "aegis.outcome": outcome})
