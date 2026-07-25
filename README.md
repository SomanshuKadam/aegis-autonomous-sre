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

## Enable Slack approval buttons

For `APPROVAL_REQUIRED` incidents, Slack can show **Approve remediation** and **Reject
remediation** buttons. Slack must be able to reach the API over a public HTTPS URL; it cannot
call `localhost` or a Docker service name.

1. Copy the Slack app's **Signing Secret** from **Basic Information** into the local `.env` file:

   ```text
   SLACK_SIGNING_SECRET=replace-with-the-signing-secret
   ```

2. Expose local API port `8081` through an HTTPS tunnel. A Cloudflare quick tunnel can be started
   from Windows with:

   ```powershell
   cloudflared tunnel --url http://127.0.0.1:8081
   ```

   Use the IPv4 loopback address shown above. It avoids `localhost` resolving to an unavailable
   IPv6 listener after WSL or Docker restarts.

3. In Slack, open **Interactivity & Shortcuts**, enable it, and set **Request URL** to:

   ```text
   https://your-public-tunnel-host/api/v1/slack/interactions
   ```

4. Save the Slack configuration, then recreate the API container so it reads the Signing Secret.
   Cloudflare quick-tunnel hostnames are temporary. Whenever the tunnel restarts, copy its new
   `https://...trycloudflare.com` hostname into Slack's Request URL.

The API verifies Slack's request signature and forwards only the exact incident and approval IDs
embedded in the Block Kit action to the internal n8n approval-resume workflow. It acknowledges a
valid button click immediately so Slack receives a response within its fixed three-second window.
The original Slack card is replaced with the recorded decision, and n8n posts the verified outcome
afterward.

An approval is valid for 15 minutes. If nobody decides within that window, Aegis expires the
approval, moves the incident to `ESCALATED`, posts an **Approval expired** card, and records that no
system change was made. The expired approval ID can never execute a remediation.

The expiry card's **Reopen approval** button creates a new 15-minute approval attempt for the same
unchanged proposal. The new attempt has a different immutable approval ID; the expired attempt
remains in the incident timeline. Approve or reject the new card normally. A successful approval
runs the bounded action once, verifies the result, resolves the incident, and posts the formatted
resolution to Slack.

Never commit `.env`, authentication material, webhook URLs, or generated SigNoz resources. The
only runtime component with mutation capability is the restricted action runner, and every action
is registered, target-validated, idempotent, policy-gated, and verified.
