from __future__ import annotations
from opentelemetry import trace
def tracer(name: str): return trace.get_tracer(name)
