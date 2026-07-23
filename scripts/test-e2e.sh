#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' 'Removing the remediation index so the scenario starts degraded...'
docker compose exec -T mongodb sh /opt/aegis/mongodb-index.sh drop

printf '%s\n' 'Generating a catalog request for the manual recovery demonstration...'
RESPONSE="$(curl -fsS 'http://localhost:8081/api/v1/products?query=aegis')"
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

printf 'Posting the bounded catalog alert for trace %s (%s ms)...\n' "$TRACE_ID" "$LATENCY"
curl -fsS -X POST 'http://localhost:5678/webhook/signoz-alert' \
  -H 'Content-Type: application/json' \
  --data "{\"fingerprint\":\"catalog-search-$TRACE_ID\",\"category\":\"catalog_search\",\"target_type\":\"mongodb_collection\",\"trace_id\":\"$TRACE_ID\",\"latency_ms\":$LATENCY}"

printf '\n%s\n' 'Alert accepted. Inspect the incident in /ops and apply only the exact approved catalog action.'
