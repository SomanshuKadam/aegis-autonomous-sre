from __future__ import annotations
from dataclasses import dataclass

@dataclass
class InvestigationBudget:
    remaining_invocations: int = 5; remaining_tool_calls: int = 20
    def consume_invocation(self) -> None:
        if self.remaining_invocations < 1: raise ValueError("AI invocation budget exhausted")
        self.remaining_invocations -= 1
    def consume_tool_call(self) -> None:
        if self.remaining_tool_calls < 1: raise ValueError("tool-call budget exhausted")
        self.remaining_tool_calls -= 1
