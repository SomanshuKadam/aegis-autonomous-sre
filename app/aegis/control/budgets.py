from __future__ import annotations
from dataclasses import dataclass, field
from datetime import timedelta
from aegis.types import utc_now

@dataclass
class InvestigationBudget:
    remaining_invocations: int = 5
    remaining_tool_calls: int = 20
    remaining_hypotheses: int = 3
    duration_seconds: int = 300
    started_at: object = field(default_factory=utc_now)

    def ensure_active(self) -> None:
        if utc_now() > self.started_at + timedelta(seconds=self.duration_seconds):
            raise ValueError("investigation duration budget exhausted")
    def consume_invocation(self) -> None:
        self.ensure_active()
        if self.remaining_invocations < 1: raise ValueError("AI invocation budget exhausted")
        self.remaining_invocations -= 1
    def consume_tool_call(self) -> None:
        self.ensure_active()
        if self.remaining_tool_calls < 1: raise ValueError("tool-call budget exhausted")
        self.remaining_tool_calls -= 1
    def consume_hypothesis(self) -> None:
        self.ensure_active()
        if self.remaining_hypotheses < 1: raise ValueError("hypothesis budget exhausted")
        self.remaining_hypotheses -= 1
