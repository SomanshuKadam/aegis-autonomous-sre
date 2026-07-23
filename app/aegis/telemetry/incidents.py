from __future__ import annotations

from time import perf_counter

from opentelemetry import metrics, trace


_tracer = trace.get_tracer("aegis.incidents")
_meter = metrics.get_meter("aegis.incidents")
_stage_counter = _meter.create_counter("aegis.incident.lifecycle.stages")


def record_stage(
    incident_id: str,
    stage: str,
    outcome: str,
    *,
    category: str = "unknown",
    source_trace_id: str | None = None,
) -> None:
    """Emit bounded lifecycle telemetry while retaining source-trace reference only."""
    started = perf_counter()
    attributes: dict[str, object] = {
        "aegis.incident_id": incident_id,
        "aegis.stage": stage,
        "aegis.outcome": outcome,
        "aegis.category": category,
    }
    if source_trace_id and len(source_trace_id) == 32:
        attributes["aegis.source_trace_id"] = source_trace_id
    with _tracer.start_as_current_span("incident.lifecycle.stage", attributes=attributes) as span:
        span.add_event("incident.stage", {"aegis.stage": stage, "aegis.outcome": outcome})
        span.set_attribute("aegis.stage.duration_ms", round((perf_counter() - started) * 1000, 3))
    _stage_counter.add(1, {"stage": stage, "outcome": outcome, "category": category})
