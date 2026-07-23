from __future__ import annotations

class CapacityState:
    def __init__(self, minimum: int = 1, maximum: int = 4, desired: int = 1) -> None:
        self.minimum = minimum; self.maximum = maximum; self.desired = desired; self.previous = desired; self.healthy = True
    def restore(self, desired: int) -> dict[str, int]:
        if not self.minimum <= desired <= self.maximum: raise ValueError("capacity is outside the configured safe range")
        self.previous = self.desired; self.desired = desired
        return {"previous": self.previous, "desired": self.desired, "minimum": self.minimum, "maximum": self.maximum}
