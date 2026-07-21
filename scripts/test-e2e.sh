#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' 'Removing the remediation index so the scenario starts degraded...'
docker compose exec -T mongodb sh /opt/aegis/mongodb-index.sh drop

printf '%s\n' 'Generating a traced request with deterministic latency above two seconds...'
RESPONSE="$(curl -fsS 'http://localhost:8081/search?q=needle')"
printf '%s\n' "$RESPONSE"

TRACE_ID="$(printf '%s\n' "$RESPONSE" | sed -n 's/.*"trace_id":"\([0-9a-f]\{32\}\)".*/\1/p')"
LATENCY="$(printf '%s\n' "$RESPONSE" | sed -n 's/.*"latency_ms":\([0-9.]*\).*/\1/p')"

if [[ ! "$TRACE_ID" =~ ^[0-9a-f]{32}$ ]]; then
  printf 'API did not return a valid trace ID. Confirm the SigNoz OTLP endpoint is reachable.\n' >&2
  exit 1
fi

if [[ ! "$LATENCY" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  printf 'API did not return a numeric latency.\n' >&2
  exit 1
fi

printf '%s\n' 'Waiting for the OpenTelemetry collector to persist the trace...'
sleep 10

printf 'Posting simulated SigNoz alert for trace %s (%s ms)...\n' "$TRACE_ID" "$LATENCY"
curl -fsS -X POST 'http://localhost:5678/webhook/signoz-alert' \
  -H 'Content-Type: application/json' \
  --data "{\"status\":\"firing\",\"trace_id\":\"$TRACE_ID\",\"alert_name\":\"Aegis API P95 latency > 2s\",\"latency_ms\":$LATENCY}"

printf '\n%s\n' 'Alert accepted. Follow the execution in n8n and the four messages in #sre-alerts.'
