from __future__ import annotations

from datetime import timedelta

from aegis.types import new_id, utc_now


class OrderQueue:
    def __init__(self, max_attempts: int = 3) -> None:
        self.jobs: list[dict[str, object]] = []
        self.max_attempts = max_attempts
    def submit(self, order_id: str) -> dict[str, object]:
        job = {"job_id": new_id(), "order_id": order_id, "state": "PENDING", "attempts": 0, "available_at": utc_now()}
        self.jobs.append(job); return job
    def claim(self) -> dict[str, object] | None:
        now = utc_now()
        self.recover_expired(now)
        for job in self.jobs:
            if job["state"] == "PENDING" and job["available_at"] <= now:
                job.update(state="CLAIMED", attempts=int(job["attempts"]) + 1, lease_until=now + timedelta(seconds=30))
                return job
        return None

    def recover_expired(self, now=None) -> int:
        now = now or utc_now()
        recovered = 0
        for job in self.jobs:
            if job["state"] == "CLAIMED" and job.get("lease_until") <= now:
                job["state"] = "PENDING" if int(job["attempts"]) < self.max_attempts else "DEAD_LETTER"
                recovered += 1
        return recovered
