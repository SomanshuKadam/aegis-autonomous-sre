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

## Run locally

This is the complete judge setup. Run the shell commands from Linux, macOS, or an Ubuntu WSL2
terminal. The project was validated with Docker Engine inside Ubuntu WSL2. On Windows, SigNoz
warns that Docker Desktop's WSL integration can cause ClickHouse Keeper crashes.

### Prerequisites

- Docker Engine with Docker Compose v2
- Git and `curl`
- WSL2 with native Docker Engine when running on Windows
- At least 6 GB of memory available to Docker for SigNoz and the application
- A ChatGPT account with Codex access or an OpenAI API key
- A Slack app with an incoming webhook for the complete notification flow
- A Slack signing secret and `cloudflared` only for the inventory approval buttons
- Free host ports `3000`, `5678`, `8000`, `8080`, `8081`, `4317`, `4318`, and `27017`

Confirm Docker is available without `sudo`:

```bash
docker version
docker compose version
```

If `docker ps` cannot reach the daemon inside WSL, start it with:

```bash
sudo service docker start
```

### 1. Clone the project

```bash
git clone https://github.com/SomanshuKadam/aegis-autonomous-sre.git
cd aegis-autonomous-sre
```

All remaining commands assume the repository root is the current directory.

### 2. Authenticate Codex

Install the Codex CLI:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

Create file-based credentials for the n8n container and complete the browser login:

```bash
codex -c cli_auth_credentials_store='"file"' login
codex login status
test -f "$HOME/.codex/auth.json"
```

The final command must succeed. `auth.json` is a secret: never commit or share it. The application
mounts it read-only into n8n so the incident workflow can run Codex non-interactively.

### 3. Deploy SigNoz and its MCP server

Install the SigNoz Foundry CLI:

```bash
curl -fsSL https://signoz.io/foundry.sh | bash
export PATH="$HOME/.local/bin:$PATH"
```

Deploy the reproducible stack from the committed casting and lock files:

```bash
foundryctl cast -f signoz/casting.yaml
```

Verify the SigNoz UI and Foundry-managed MCP server:

```bash
curl -fsS http://localhost:8080/ >/dev/null && echo "SigNoz UI reachable"
curl -fsS http://localhost:8000/livez
```

Open [http://localhost:8080](http://localhost:8080), create the first administrator account, then
open **Settings → Service Accounts** and create an API key. Keep the key for the next step.

Foundry creates the external Docker network named `signoz-network`. The application joins that
network so Codex can reach the Foundry-managed `signoz-mcp` service.

### 4. Configure the application

```bash
cp .env.example .env
printf 'Codex auth path: %s\n' "$HOME/.codex/auth.json"
printf 'Docker socket group ID: %s\n' \
  "$(stat -c '%g' /var/run/docker.sock 2>/dev/null || stat -f '%g' /var/run/docker.sock)"
```

Edit `.env` and replace every placeholder. These values are required for the complete demo:

```dotenv
MONGO_ROOT_PASSWORD=<local-password>
N8N_ENCRYPTION_KEY=<local-encryption-key>
N8N_PASSWORD=<local-admin-password>
SIGNOZ_API_KEY=<signoz-service-account-key>
CODEX_AUTH_FILE=/home/<your-linux-user>/.codex/auth.json
DOCKER_GID=<printed-docker-socket-group-id>
AEGIS_ORCHESTRATOR_TOKEN=<local-random-token>
AEGIS_OPERATOR_TOKEN=<different-local-random-token>
AEGIS_RUNNER_TOKEN=<different-local-random-token>
SLACK_WEBHOOK_URL=<slack-incoming-webhook-url>
SLACK_SIGNING_SECRET=<slack-app-signing-secret>
```

Use different values for the three control-plane tokens. They separate orchestration, operator,
and runner capabilities. `DOCKER_GID` lets the non-root n8n user invoke the isolated Docker action
runner through the local socket.

Generate suitably random local values with `openssl rand -hex 32`. Run it once for the n8n
encryption key and once for each control-plane token.

To obtain the Slack values:

1. Create or open a Slack app and enable **Incoming Webhooks**.
2. Add a webhook to the channel that should receive incident cards and copy its URL.
3. Copy **Basic Information → App Credentials → Signing Secret**.

The webhook is required because each lifecycle stage records its Slack delivery. The signing
secret is required only when approving or rejecting the inventory remediation from Slack.

### 5. Start Aegis and publish the n8n workflow

```bash
docker compose config --quiet
docker compose up -d --build
bash scripts/import-workflow.sh
docker compose ps
```

The import helper waits for n8n to become ready, imports the committed workflow, and publishes it.
The application containers should be running, and services with health checks should report
`healthy`.

Verify the control plane and UI:

```bash
curl -fsS http://localhost:8081/health
curl -fsS http://localhost:3000/healthz
```

Open the local surfaces:

| Surface | URL |
| --- | --- |
| Operations overview | [http://localhost:3000/ops](http://localhost:3000/ops) |
| Workload shop | [http://localhost:3000/shop](http://localhost:3000/shop) |
| SigNoz | [http://localhost:8080](http://localhost:8080) |
| n8n | [http://localhost:5678](http://localhost:5678) |

The normal workload creates an order every 30 seconds so traces and service charts continue to
move when no incident demonstration is running.

### 6. Run a self-healing demonstration

Run one scenario at a time from WSL:

```bash
bash scripts/demo/simulate-self-healing.sh catalog
bash scripts/demo/simulate-self-healing.sh inventory
bash scripts/demo/simulate-self-healing.sh backlog
```

Each command creates a real local failure condition, waits for telemetry ingestion, submits the
correlated signal to n8n, and prints the incident and trace identifiers.

Follow the result in three places:

1. Slack shows detection, Codex diagnosis, the bounded action, and the verified outcome.
2. The incident page shows the expandable recovery lifecycle.
3. SigNoz shows the source trace and surrounding telemetry used during investigation.

### Catalog

```bash
bash scripts/demo/simulate-self-healing.sh catalog
```

The scenario removes only the registered search index and generates a slow customer search. The
runner may recreate that exact index. A fresh search must return below the configured recovery
threshold before resolution.

### Inventory

```bash
bash scripts/demo/simulate-self-healing.sh inventory
```

Parallel orders exhaust inventory reservation capacity. Codex may propose
`inventory.restore_capacity@1`, but policy pauses the incident at `APPROVAL_REQUIRED`. Nothing is
changed until the exact approval is accepted.

### Backlog

```bash
bash scripts/demo/simulate-self-healing.sh backlog
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

### 7. Enable Slack approval buttons

Slack cannot send interactive actions to `localhost`. Install
[cloudflared](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/),
then start a temporary HTTPS tunnel:

```bash
cloudflared tunnel --url http://127.0.0.1:8081
```

Keep that process running. In the Slack app, enable **Interactivity & Shortcuts** and set its
request URL to:

```text
https://<temporary-host>.trycloudflare.com/api/v1/slack/interactions
```

Save the Slack setting. If `SLACK_SIGNING_SECRET` was added after the application started,
recreate only the API service:

```bash
docker compose up -d --no-deps --force-recreate api
```

The API verifies Slack's signature, records the decision, and acknowledges the click immediately.
n8n resumes the longer remediation asynchronously.

An unanswered approval expires after 15 minutes without executing anything. Reopening it creates
a new immutable approval identifier while preserving the expired attempt in the incident record.

### Stop the local deployment

Stop the application while preserving its local volumes:

```bash
docker compose down
```

Stop the Foundry-rendered SigNoz deployment separately:

```bash
docker compose -f pours/deployment/compose.yaml down
```

Do not add `--volumes` unless the local incident and telemetry data should be deleted.

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
