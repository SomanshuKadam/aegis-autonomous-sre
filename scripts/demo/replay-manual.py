"""Manually confirm every sanitized replay fixture has zero side effects."""
from __future__ import annotations
import os
from pathlib import Path
import httpx

def main() -> None:
    headers = {"Authorization": f"Bearer {os.environ['AEGIS_OPERATOR_TOKEN']}"}
    fixture_dir = Path("/app/aegis/examples/replay/fixtures")
    fixture_ids = [path.stem for path in fixture_dir.glob("*.json")]
    if not fixture_ids:
        raise RuntimeError("no replay fixtures are available in the API container")
    with httpx.Client(timeout=15) as client:
        for fixture_id in fixture_ids:
            response = client.get(f"http://api:8081/api/v1/evaluation/replays/{fixture_id}", headers=headers)
            response.raise_for_status(); result = response.json()
            if not result.get("expected_matched") or result.get("live_mutations") != 0 or result.get("external_notifications") != 0:
                raise RuntimeError(f"unsafe replay result for {fixture_id}: {result}")
    print(f"replay-manual-ok fixtures={len(fixture_ids)}")

if __name__ == "__main__": main()
