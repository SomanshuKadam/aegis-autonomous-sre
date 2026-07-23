from __future__ import annotations

class RollbackGuard:
    def __init__(self) -> None: self.completed: set[str] = set()
    def compensate(self, execution_id: str, previous_state: dict[str, object]) -> dict[str, object]:
        if execution_id in self.completed: raise ValueError("rollback was already attempted")
        self.completed.add(execution_id)
        return {"outcome": "ROLLED_BACK", "restored": previous_state}
