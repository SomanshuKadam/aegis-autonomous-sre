from __future__ import annotations
from aegis.inventory.capacity import CapacityState

def restore_capacity(state: CapacityState, target: int) -> dict[str, int]:
    return state.restore(target)
