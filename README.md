# Aegis reliability platform

Aegis is a local commerce application with a bounded reliability control plane. Its operations
console shows application health and the durable incident lifecycle; SigNoz remains the
authoritative telemetry explorer and n8n handles alert delivery, approval resume, and notification
recording.

This is a hackathon prototype. It has no automated-test workflow. Validation is intentionally
limited to production builds, Compose service health, and the manual demonstrations below.

## Use the UI

With the stack already running, open `http://localhost:3000/shop` to browse products and submit a
normal order. Open `http://localhost:3000/ops` to view live service health, workload activity,
and historical incidents. Open an incident to inspect its evidence, policy decision, approval,
execution, verification or rollback, notification status, and authenticated SigNoz context links.

The operations console contains no customer-facing control for manufacturing faults or applying a
repair. The three bounded demonstrations are reviewer-operated backend walkthroughs.

## Run a manual demonstration

Run these only against the local Compose stack. Each command prints an incident and, where
available, a trace correlation ID to use in the operations console and SigNoz.

```bash
docker compose cp scripts/demo/catalog-auto-recovery-demo.py api:/tmp/catalog-auto-recovery-demo.py
docker compose exec -T api python /tmp/catalog-auto-recovery-demo.py

docker compose cp scripts/demo/inventory-approval-demo.py api:/tmp/inventory-approval-demo.py
docker compose exec -T api python /tmp/inventory-approval-demo.py

docker compose cp scripts/demo/backlog-recovery-demo.py api:/tmp/backlog-recovery-demo.py
docker compose exec -T api python /tmp/backlog-recovery-demo.py

docker compose cp scripts/demo/backlog-safe-refusal-demo.py api:/tmp/backlog-safe-refusal-demo.py
docker compose exec -T api python /tmp/backlog-safe-refusal-demo.py
```

Catalog recovery grows local demo data, observes a real slow customer search after removing only
the registered index, then verifies the lifecycle recreates exactly `products.search_text_1`.
Inventory recovery creates ordinary order pressure, pauses for the exact approval, verifies a
fresh order, and restores the pre-demo capacity. Backlog recovery adds one bounded worker capacity
step only when healthy headroom exists; the refusal walkthrough proves an already-maxed worker
pool is escalated without mutation.

For an n8n approval resume and notification-recording walkthrough, run:

```bash
docker compose cp scripts/demo/n8n-approval-resume-demo.py api:/tmp/n8n-approval-resume-demo.py
docker compose exec -T api python /tmp/n8n-approval-resume-demo.py
```

If Slack is not configured, the workflow records a failed Slack notification independently while
the incident’s technical result remains visible in Aegis.

## Production build and workflow import

```bash
npm --prefix frontend run build
docker compose config --quiet
docker compose exec -T n8n n8n import:workflow --input=/opt/aegis/workflows/aegis-autonomous-sre.json
docker compose exec -T n8n n8n publish:workflow --id=aegis-autonomous-lifecycle-v2
```

## Run the self-healing workflow

The commerce application is only the observable workload. The Aegis product is the incident
workflow: a correlated signal enters n8n, Slack receives the trigger, Codex investigates the
source trace through read-only SigNoz access, deterministic policy checks the proposed registered
action, the isolated runner applies it, and a fresh verification result is reported to Slack.

From WSL, create one real local condition and submit its correlated signal to the active n8n
webhook:

```bash
./scripts/demo/simulate-self-healing.sh catalog
./scripts/demo/simulate-self-healing.sh inventory
./scripts/demo/simulate-self-healing.sh backlog
```

Use `catalog` for the shortest automatic end-to-end demonstration. `inventory` intentionally
stops at explicit approval because its registered action is medium risk. The script prints the
source trace and Aegis incident URL; Slack shows detection, Codex diagnosis, the bounded action,
and the verified outcome as separate cards.

Never commit `.env`, authentication material, webhook URLs, or generated SigNoz resources. The
only runtime component with mutation capability is the restricted action runner, and every action
is registered, target-validated, idempotent, policy-gated, and verified.
