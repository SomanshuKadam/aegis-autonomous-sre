from __future__ import annotations

from datetime import timedelta

from aegis.types import new_id, utc_now


class OrderQueue:
    def __init__(self) -> None: self.jobs: list[dict[str, object]] = []
    def submit(self, order_id: str) -> dict[str, object]:
        job = {"job_id": new_id(), "order_id": order_id, "state": "PENDING", "attempts": 0, "available_at": utc_now()}
        self.jobs.append(job); return job
    def claim(self) -> dict[str, object] | None:
        now = utc_now()
        for job in self.jobs:
            if job["state"] == "PENDING" and job["available_at"] <= now:
                job.update(state="PROCESSING", attempts=int(job["attempts"]) + 1, lease_until=now + timedelta(seconds=30))
                return job
        return None
