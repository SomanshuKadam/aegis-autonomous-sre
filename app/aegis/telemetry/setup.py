from __future__ import annotations
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

def configure(service_name: str, environment: str) -> None:
    provider = TracerProvider(resource=Resource.create({"service.name": service_name, "deployment.environment": environment}))
    trace.set_tracer_provider(provider)

def tracer(name: str): return trace.get_tracer(name)
