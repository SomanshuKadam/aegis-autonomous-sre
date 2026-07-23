from __future__ import annotations
from aegis.worker.capacity import WorkerCapacity

def increase_capacity(state: WorkerCapacity, increment: int = 1) -> dict[str, int]:
    if increment != 1: raise ValueError("worker capacity may increase by one bounded step")
    return state.increase(increment)
