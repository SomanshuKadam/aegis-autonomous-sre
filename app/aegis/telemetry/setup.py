from __future__ import annotations
from opentelemetry import metrics, trace
from opentelemetry.context import Context
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace import Link, SpanContext, TraceFlags
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def configure(service_name: str, environment: str, endpoint: str | None = None) -> None:
    resource = Resource.create({"service.name": service_name, "deployment.environment": environment})
    trace_provider = TracerProvider(resource=resource)
    if endpoint:
        trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(trace_provider)
    metrics.set_meter_provider(MeterProvider(resource=resource))
    set_global_textmap(TraceContextTextMapPropagator())

def tracer(name: str): return trace.get_tracer(name)

def span_link(trace_id: str, span_id: str) -> Link:
    context = SpanContext(
        trace_id=int(trace_id, 16),
        span_id=int(span_id, 16),
        is_remote=True,
        trace_flags=TraceFlags.SAMPLED,
    )
    return Link(context)
