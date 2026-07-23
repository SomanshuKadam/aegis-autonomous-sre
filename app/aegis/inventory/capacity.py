from __future__ import annotations

class CapacityState:
    def __init__(self, minimum: int = 1, maximum: int = 4, desired: int = 1) -> None:
        self.minimum = minimum; self.maximum = maximum; self.desired = desired
    def restore(self, desired: int) -> dict[str, int]:
        if not self.minimum <= desired <= self.maximum: raise ValueError("capacity is outside the configured safe range")
        previous = self.desired; self.desired = desired
        return {"previous": previous, "desired": self.desired}
