"""Manually prove a demo condition can be exposed only once per durable run."""
from __future__ import annotations
import os
import httpx

def main() -> None:
    headers = {"Authorization": f"Bearer {os.environ['AEGIS_OPERATOR_TOKEN']}"}
    url = "http://api:8081/api/v1/workloads/demo/demo-validation-20260724/conditions/inventory_saturation"
    with httpx.Client(timeout=15) as client:
        first = client.post(url, headers=headers); first.raise_for_status()
        second = client.post(url, headers=headers); second.raise_for_status()
    if not first.json().get("exposed") or second.json().get("exposed"):
        raise RuntimeError("demo condition marker was not once-per-run")
    print("demo-marker-manual-ok")

if __name__ == "__main__": main()
