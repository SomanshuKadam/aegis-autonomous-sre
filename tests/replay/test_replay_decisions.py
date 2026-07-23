from pathlib import Path
from aegis.control.fixtures import load_fixture
from aegis.control.replay import evaluate_fixture

def test_replay_is_non_mutating_and_deterministic() -> None:
    root = Path("/app/tests/replay/fixtures") if Path("/app/tests/replay/fixtures").exists() else Path("tests/replay/fixtures")
    valid = evaluate_fixture(load_fixture(root / "catalog-valid.json")); blocked = evaluate_fixture(load_fixture(root / "missing-evidence.json"))
    assert valid["outcome"] == "AUTO_APPROVED" and blocked["outcome"] == "BLOCKED"
    assert valid["live_mutations"] == blocked["external_notifications"] == 0
