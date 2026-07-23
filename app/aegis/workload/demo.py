from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class DemoMarker:
    scenario: str
    run_id: str
    seed: int
    ordinal: int


class DemoWorkload:
    """Deterministic, once-per-run traffic plans for manual hackathon demonstrations."""
    def __init__(self, run_id: str, seed: int) -> None:
        self.run_id, self.seed, self.random, self.completed = run_id, seed, Random(seed), set()

    def catalog_growth(self, count: int = 50) -> list[dict[str, str]]:
        return [{"sku": f"demo-{self.seed}-{item}", "search_text": f"aegis demo searchable item {item}"} for item in range(count)]

    def search_terms(self, count: int = 20) -> list[str]:
        return [f"aegis demo {self.random.randrange(50)}" for _ in range(count)]

    def once(self, scenario: str) -> DemoMarker | None:
        if scenario in self.completed:
            return None
        self.completed.add(scenario)
        return DemoMarker(scenario, self.run_id, self.seed, len(self.completed))
