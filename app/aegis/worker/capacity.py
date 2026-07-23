from __future__ import annotations
from aegis.inventory.capacity import CapacityState

class WorkerCapacity(CapacityState):
    def __init__(self, minimum: int = 1, maximum: int = 8, desired: int = 1) -> None:
        super().__init__(minimum, maximum, desired); self.observed = desired
    def increase(self, increment: int = 1) -> dict[str, int]:
        result = self.restore(min(self.maximum, self.desired + increment)); self.observed = self.desired; return result | {"observed": self.observed}
