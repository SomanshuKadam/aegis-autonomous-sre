from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from aegis.types import new_id

@dataclass
class WorkloadRun:
    run_id: str; seed: int; enabled: bool; demo: bool = False; generated_orders: int = 0

class WorkloadService:
    def __init__(self, state_path: str = "/tmp/aegis-workload-runs.json") -> None:
        self.state_path = Path(state_path); self.runs: dict[str, WorkloadRun] = {}; self._load()
    def _load(self) -> None:
        if self.state_path.exists():
            self.runs = {item["run_id"]: WorkloadRun(**item) for item in json.loads(self.state_path.read_text())}
    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps([asdict(run) for run in self.runs.values()]))
    def start(self, seed: int = 1, demo: bool = False) -> WorkloadRun:
        run = WorkloadRun(new_id(), seed, True, demo); self.runs[run.run_id] = run; self._save(); return run
    def stop(self, run_id: str) -> WorkloadRun:
        run = self.runs[run_id]; run.enabled = False; self._save(); return run
    def record_order(self, run_id: str) -> WorkloadRun:
        run = self.runs[run_id]; run.generated_orders += 1; self._save(); return run
