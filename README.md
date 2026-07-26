# Aegis

Self-healing incident response powered by SigNoz, OpenTelemetry, Codex, n8n, and Slack.

Aegis turns an observable failure into a controlled recovery:

1. SigNoz captures the failing trace and live service evidence.
2. n8n opens a durable incident and notifies Slack.
3. Codex investigates through read-only SigNoz MCP access.
4. Deterministic policy checks the proposed registered action.
5. Low-risk actions run automatically; higher-risk actions wait for Slack approval.
6. An isolated runner applies the bounded change.
7. Fresh business behavior must prove recovery before the incident is resolved.

The included commerce workload exists to produce realistic traces, dependency failures, and queue
pressure. The main product is the incident workflow around it.

## What the demo shows

| Scenario | Signal | Bounded response | Decision |
| --- | --- | --- | --- |
| Catalog search | Slow search with the expected MongoDB index absent | Recreate only `products.search_text_1` | Automatic |
| Inventory dependency | Reservation capacity exhausted and orders returning dependency errors | Restore the recorded safe capacity | Slack approval |
| Order backlog | Old queued orders, healthy workers, and available headroom | Add one worker-capacity step | Automatic |
| Unsafe backlog | Workers unhealthy or already at maximum capacity | No mutation | Escalate |

Every path records detection, investigation, policy, execution, verification, notification, and
rollback information in an append-only incident timeline.

## Architecture

```text
Commerce workload ──OpenTelemetry──> SigNoz
        │                                │
        │ correlated signal              │ read-only MCP investigation
        ▼                                ▼
       n8n ────────────────> Codex structured diagnosis
        │                                │
        ├──> Slack                       ▼
        │                       deterministic policy
        │                                │
        │                 ┌──────────────┴──────────────┐
        │                 │                             │
        │          automatic action              Slack approval
        │                 │                             │
        └─────────────────┴──────────────┬──────────────┘
                                        ▼
                               isolated action runner
                                        │
                                        ▼
                              fresh recovery verification
```

SigNoz remains the telemetry explorer. The Aegis UI presents the operational lifecycle without
duplicating trace, log, service, or dashboard exploration.

## Prerequisites

- Docker Engine with Docker Compose v2
- WSL2 when running on Windows
- At least 4 GB available to the SigNoz stack
- Codex CLI authentication
- A SigNoz service-account API key
- A Slack incoming webhook for notifications
- A Slack signing secret and public HTTPS tunnel only when testing approval buttons

## 1. Start SigNoz

Install the SigNoz Foundry CLI:

```bash
curl -fsSL https://signoz.io/foundry.sh | bash
export PATH="$HOME/.local/bin:$PATH"
```

Create the local SigNoz stack from the repository casting file:

```bash
foundryctl cast -f signoz/casting.yaml
```

Open SigNoz at [http://localhost:8080](http://localhost:8080), create a service account, and copy
its API key.

## 2. Configure Aegis

```bash
git clone https://github.com/SomanshuKadam/aegis-autonomous-sre.git
cd aegis-autonomous-sre
cp .env.example .env
```

Set the required values in `.env`:

```dotenv
MONGO_ROOT_PASSWORD=<local-password>
N8N_ENCRYPTION_KEY=<local-encryption-key>
N8N_PASSWORD=<local-admin-password>
SIGNOZ_API_KEY=<signoz-service-account-key>
CODEX_AUTH_FILE=<absolute-wsl-path-to-codex-auth.json>
AEGIS_ORCHESTRATOR_TOKEN=<local-random-token>
AEGIS_OPERATOR_TOKEN=<different-local-random-token>
AEGIS_RUNNER_TOKEN=<different-local-random-token>
SLACK_WEBHOOK_URL=<optional-slack-incoming-webhook>
SLACK_SIGNING_SECRET=<required-only-for-slack-buttons>
```

Use different values for the three control-plane tokens. They separate orchestration, operator,
and runner capabilities.

## 3. Start the application

```bash
docker compose up -d --build
./scripts/import-workflow.sh
```

Open:

| Surface | URL |
| --- | --- |
| Operations overview | [http://localhost:3000/ops](http://localhost:3000/ops) |
| Workload shop | [http://localhost:3000/shop](http://localhost:3000/shop) |
| SigNoz | [http://localhost:8080](http://localhost:8080) |
| n8n | [http://localhost:5678](http://localhost:5678) |

The normal workload creates an order every 30 seconds so traces and service charts continue to
move when no incident demonstration is running.

## 4. Run the self-healing demonstrations

Run one scenario at a time from WSL:

```bash
./scripts/demo/simulate-self-healing.sh catalog
./scripts/demo/simulate-self-healing.sh inventory
./scripts/demo/simulate-self-healing.sh backlog
```

Each command creates a real local failure condition, waits for telemetry ingestion, submits the
correlated signal to n8n, and prints the incident and trace identifiers.

Follow the result in three places:

1. Slack shows detection, Codex diagnosis, the bounded action, and the verified outcome.
2. The incident page shows the expandable recovery lifecycle.
3. SigNoz shows the source trace and surrounding telemetry used during investigation.

### Catalog

```bash
./scripts/demo/simulate-self-healing.sh catalog
```

The scenario removes only the registered search index and generates a slow customer search. The
runner may recreate that exact index. A fresh search must return below the configured recovery
threshold before resolution.

### Inventory

```bash
./scripts/demo/simulate-self-healing.sh inventory
```

Parallel orders exhaust inventory reservation capacity. Codex may propose
`inventory.restore_capacity@1`, but policy pauses the incident at `APPROVAL_REQUIRED`. Nothing is
changed until the exact approval is accepted.

### Backlog

```bash
./scripts/demo/simulate-self-healing.sh backlog
```

The scenario creates enough orders for the oldest queued item to exceed 30 seconds. Capacity is
increased by one step only when workers are healthy, below their maximum, and reporting resource
headroom.

The explicit refusal walkthrough is also available:

```bash
docker compose cp scripts/demo/backlog-safe-refusal-demo.py api:/tmp/backlog-safe-refusal-demo.py
docker compose exec -T api python /tmp/backlog-safe-refusal-demo.py
```

It proves that an unhealthy or maxed worker pool is escalated without execution.

## Slack approval buttons

Slack cannot send interactive actions to `localhost`. Start a temporary HTTPS tunnel:

```powershell
cloudflared tunnel --url http://127.0.0.1:8081
```

In the Slack app, enable **Interactivity & Shortcuts** and set the request URL to:

```text
https://<temporary-host>.trycloudflare.com/api/v1/slack/interactions
```

After setting `SLACK_SIGNING_SECRET`, recreate the API service:

```bash
docker compose up -d --no-deps --force-recreate api
```

The API verifies Slack's signature, records the decision, and acknowledges the click immediately.
n8n resumes the longer remediation asynchronously.

An unanswered approval expires after 15 minutes without executing anything. Reopening it creates
a new immutable approval identifier while preserving the expired attempt in the incident record.

## Repository layout

```text
app/                 FastAPI control plane, workload services, policy, and runner
frontend/            React operations console and workload shop
mongodb/             Local database initialization
n8n/workflows/       Incident lifecycle workflow
codex/               Structured agent output schemas
scripts/demo/        Reproducible incident scenarios
signoz/              Local SigNoz Foundry configuration
docker-compose.yml   Application service topology
```

## Safety boundaries

- Codex receives read-only SigNoz MCP access.
- Agent output must match a versioned JSON schema.
- Only registered actions with exact targets can reach policy.
- Only the isolated runner can mutate service state.
- Approval identifiers are immutable and single-use.
- Every action is idempotent and bounded.
- Recovery is based on fresh behavior, not command exit status.
- Failed verification triggers rollback or escalation.

## AI assistance disclosure

OpenAI Codex was used to help with the development of this project.

## Built for Agents of SigNoz

Aegis combines end-to-end AI-agent observability, a SigNoz MCP investigation sidekick, an n8n
incident workflow, and policy-bounded self-healing infrastructure in one local demonstration.
