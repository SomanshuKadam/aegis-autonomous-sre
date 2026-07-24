"""Create a real local reliability condition and send its correlated alert through n8n."""

from __future__ import annotations

import concurrent.futures
import os
import subprocess
import sys
import time
from pathlib import Path
from secrets import token_hex
from uuid import uuid4

import httpx
from pymongo import MongoClient


API_URL = os.getenv("AEGIS_API_URL", "http://api:8081").rstrip("/")
N8N_URL = os.getenv("AEGIS_N8N_URL", "http://n8n:5678").rstrip("/")
SCENARIOS = {"catalog", "inventory", "backlog"}


def traceparent(trace_id: str) -> str:
    return f"00-{trace_id}-{token_hex(8)}-01"


def create_order(sequence: int) -> tuple[int, str]:
    trace_id = token_hex(16)
    response = httpx.post(
        f"{API_URL}/api/v1/orders",
        headers={
            "Idempotency-Key": f"aegis-scenario-{uuid4()}-{sequence}",
            "traceparent": traceparent(trace_id),
        },
        json={"sku": "sku-002", "quantity": 1},
        timeout=20,
    )
    return response.status_code, trace_id


LoadControl = tuple[subprocess.Popen[bytes], Path]
Condition = tuple[str, str, dict[str, str], LoadControl | None]


def catalog_condition(client: httpx.Client) -> Condition:
    mongo = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=5000)
    products = mongo[os.getenv("MONGO_DATABASE", "mydatabase")]["products"]
    if "search_text_1" in products.index_information():
        products.drop_index("search_text_1")
    signal = client.get(f"{API_URL}/api/v1/catalog/search").json()
    if signal.get("index_present") or float(signal.get("latency_ms", 0)) < 2000:
        raise RuntimeError(f"catalog degradation was not produced: {signal}")
    return (
        "catalog_search",
        str(signal["trace_id"]),
        {
            "type": "mongodb_collection",
            "database": "mydatabase",
            "collection": "products",
            "field": "search_text",
        },
        None,
    )


def inventory_condition(_: httpx.Client) -> Condition:
    health = httpx.get("http://inventory:8082/health", timeout=10).json()
    mongo = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=5000)
    executions = mongo[os.getenv("MONGO_DATABASE", "mydatabase")]["runner_executions"]
    while int(health["capacity"]) > 1:
        current = int(health["capacity"])
        prior = executions.find_one(
            {
                "action_key": "inventory.restore_capacity@1",
                "state": {"$in": ["SUCCEEDED", "NOOP"]},
                "rollback_claimed": {"$ne": True},
                "result.desired": current,
                "result.previous_state.desired": {"$lt": current},
            },
            sort=[("_id", -1)],
        )
        if prior is None:
            raise RuntimeError(
                f"inventory capacity is {current}, but no exact unconsumed registered execution can compensate it"
            )
        baseline = httpx.post(
            "http://action-runner:8085/actions/rollback",
            headers={"Authorization": f"Bearer {os.environ['AEGIS_RUNNER_TOKEN']}"},
            json={
                "action_key": "inventory.restore_capacity@1",
                "target": {"type": "inventory_dependency"},
                "previous_state": prior["result"]["previous_state"],
                "idempotency_key": prior["idempotency_key"],
            },
            timeout=30,
        )
        baseline.raise_for_status()
        health = httpx.get("http://inventory:8082/health", timeout=10).json()
    if int(health["capacity"]) != 1:
        raise RuntimeError(f"registered compensation did not establish the capacity-1 baseline: {health}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(create_order, range(12)))
    failed = [trace_id for status, trace_id in results if status >= 400]
    if not failed:
        raise RuntimeError("inventory saturation was not produced; retry when capacity is one")
    httpx.get(
        "http://inventory:8082/health",
        headers={"traceparent": traceparent(failed[0])},
        timeout=10,
    ).raise_for_status()
    stop_path = Path(f"/tmp/aegis-inventory-load-{uuid4().hex}.stop")
    process = subprocess.Popen(
        [sys.executable, __file__, "_inventory_load", str(stop_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return "inventory_dependency", failed[0], {"type": "inventory_dependency"}, (process, stop_path)


def sustain_inventory_load(stop_path: Path) -> None:
    deadline = time.monotonic() + 600
    sequence = 1000
    while time.monotonic() < deadline and not stop_path.exists():
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(create_order, range(sequence, sequence + 3)))
        sequence += 3
        time.sleep(1.5)


def backlog_condition(client: httpx.Client) -> Condition:
    worker = client.get("http://worker:8083/health").json()
    mongo = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=5000)
    executions = mongo[os.getenv("MONGO_DATABASE", "mydatabase")]["runner_executions"]
    while int(worker["capacity"]) > 1:
        current = int(worker["capacity"])
        prior = executions.find_one(
            {
                "action_key": "worker.set_capacity@1",
                "state": {"$in": ["SUCCEEDED", "NOOP"]},
                "rollback_claimed": {"$ne": True},
                "result.desired": current,
                "result.previous_state.desired": {"$lt": current},
            },
            sort=[("_id", -1)],
        )
        if prior is None:
            raise RuntimeError(
                f"worker capacity is {current}, but no exact unconsumed registered execution can compensate it"
            )
        rollback = client.post(
            "http://action-runner:8085/actions/rollback",
            headers={"Authorization": f"Bearer {os.environ['AEGIS_RUNNER_TOKEN']}"},
            json={
                "action_key": "worker.set_capacity@1",
                "target": {"type": "order_worker"},
                "previous_state": prior["result"]["previous_state"],
                "idempotency_key": prior["idempotency_key"],
            },
        )
        rollback.raise_for_status()
        worker = client.get("http://worker:8083/health").json()
    traces: list[str] = []
    for sequence in range(140):
        status, trace_id = create_order(sequence)
        if status == 201:
            traces.append(trace_id)
        else:
            time.sleep(0.2)
    if not traces:
        raise RuntimeError("backlog demand did not create any orders")
    deadline = time.monotonic() + 50
    health = client.get("http://worker:8083/health").json()
    while time.monotonic() < deadline:
        if int(health["queue_depth"]) > 0 and int(health["oldest_age_seconds"]) >= 30:
            break
        time.sleep(1)
        health = client.get("http://worker:8083/health").json()
    if not (int(health["queue_depth"]) > 0 and int(health["oldest_age_seconds"]) >= 30):
        raise RuntimeError(f"an aged backlog was not produced: {health}")
    client.get(
        "http://worker:8083/health",
        headers={"traceparent": traceparent(traces[-1])},
    ).raise_for_status()
    return "order_backlog", traces[-1], {"type": "order_worker"}, None


def stop_inventory_load(control: LoadControl | None) -> None:
    if control is None:
        return
    process, stop_path = control
    stop_path.touch()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.terminate()
        process.wait(timeout=5)
    stop_path.unlink(missing_ok=True)


def wait_for_inventory_decision(client: httpx.Client, incident_id: str, control: LoadControl) -> str:
    deadline = time.monotonic() + 360
    terminal = {"APPROVAL_REQUIRED", "RESOLVED", "BLOCKED", "ESCALATED", "FAILED", "ROLLED_BACK"}
    process, _ = control
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("inventory pressure worker exited before the workflow reached its decision gate")
        response = client.get(f"{API_URL}/api/v1/orchestration/incidents/{incident_id}")
        response.raise_for_status()
        state = str(response.json()["state"])
        if state in terminal:
            return state
        time.sleep(2)
    raise RuntimeError("inventory workflow did not reach approval or a terminal state within 360 seconds")


def find_incident(client: httpx.Client, fingerprint: str) -> dict[str, object]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        response = client.get(f"{API_URL}/api/v1/orchestration/incidents")
        response.raise_for_status()
        for incident in response.json()["items"]:
            if incident.get("fingerprint") == fingerprint:
                return incident
        time.sleep(0.5)
    raise RuntimeError("n8n accepted the alert but the incident was not registered within 30 seconds")


def main() -> None:
    scenario = sys.argv[1].lower() if len(sys.argv) > 1 else "catalog"
    if scenario == "_inventory_load":
        if len(sys.argv) != 3:
            raise SystemExit("inventory load worker requires a stop-file path")
        sustain_inventory_load(Path(sys.argv[2]))
        return
    if scenario not in SCENARIOS:
        raise SystemExit("usage: simulate-self-healing.py catalog|inventory|backlog")
    factories = {
        "catalog": catalog_condition,
        "inventory": inventory_condition,
        "backlog": backlog_condition,
    }
    with httpx.Client(timeout=30) as client:
        load_control: LoadControl | None = None
        try:
            category, trace_id, target, load_control = factories[scenario](client)
            fingerprint = f"aegis-{scenario}-{uuid4().hex}"
            print(f"condition-created scenario={scenario} trace={trace_id}", flush=True)
            print("waiting 12 seconds for telemetry ingestion before notifying n8n", flush=True)
            time.sleep(12)
            alert = client.post(
                f"{N8N_URL}/webhook/aegis-lifecycle-alert",
                json={
                    "status": "firing",
                    "alert_name": {
                        "catalog": "Catalog search P95 exceeded 2 seconds",
                        "inventory": "Inventory dependency error rate exceeded threshold",
                        "backlog": "Order queue oldest age exceeded 30 seconds",
                    }[scenario],
                    "fingerprint": fingerprint,
                    "category": category,
                    "target": target,
                    "trace_id": trace_id,
                },
            )
            alert.raise_for_status()
            incident = find_incident(client, fingerprint)
            if scenario == "inventory":
                if load_control is None:
                    raise RuntimeError("inventory scenario did not start its pressure worker")
                final_state = wait_for_inventory_decision(client, str(incident["incident_id"]), load_control)
            else:
                final_state = str(incident["state"])
        finally:
            stop_inventory_load(load_control)
    print(f"workflow-started incident={incident['incident_id']} trace={trace_id}")
    if scenario == "inventory":
        print(f"inventory-gate-state={final_state}")
    print(f"open=http://localhost:3000/ops/incidents/{incident['incident_id']}")
    print("watch Slack for detection, Codex diagnosis, remediation plan, and verified outcome")


if __name__ == "__main__":
    main()
