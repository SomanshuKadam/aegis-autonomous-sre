from aegis.workload.service import WorkloadService

def test_workload_run_is_seeded_and_stoppable() -> None:
    service = WorkloadService(); run = service.start(seed=42)
    assert run.seed == 42 and service.stop(run.run_id).enabled is False
