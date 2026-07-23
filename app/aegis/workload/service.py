from __future__ import annotations
from dataclasses import dataclass
from aegis.types import new_id

@dataclass
class WorkloadRun:
    run_id: str; seed: int; enabled: bool; demo: bool = False

class WorkloadService:
    def __init__(self) -> None: self.runs: dict[str, WorkloadRun] = {}
    def start(self, seed: int = 1, demo: bool = False) -> WorkloadRun:
        run = WorkloadRun(new_id(), seed, True, demo); self.runs[run.run_id] = run; return run
    def stop(self, run_id: str) -> WorkloadRun:
        run = self.runs[run_id]; run.enabled = False; return run
