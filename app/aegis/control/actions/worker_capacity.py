from __future__ import annotations
from aegis.worker.capacity import WorkerCapacity

def increase_capacity(state: WorkerCapacity, increment: int = 1) -> dict[str, int]:
    return state.increase(increment)
