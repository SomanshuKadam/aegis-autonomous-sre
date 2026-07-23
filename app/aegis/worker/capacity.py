from __future__ import annotations
from aegis.inventory.capacity import CapacityState

class WorkerCapacity(CapacityState):
    def increase(self, increment: int = 1) -> dict[str, int]:
        return self.restore(min(self.maximum, self.desired + increment))
