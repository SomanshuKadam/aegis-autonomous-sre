#!/usr/bin/env bash
set -euo pipefail

attempt=0
until docker compose exec -T n8n node -e \
  "fetch('http://127.0.0.1:5678/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 60 ]; then
    printf '%s\n' 'n8n did not become ready within 120 seconds.' >&2
    exit 1
  fi
  sleep 2
done

docker compose exec -T n8n n8n import:workflow \
  --input=/opt/aegis/workflows/aegis-autonomous-sre.json

docker compose exec -T n8n n8n publish:workflow \
  --id=aegis-autonomous-lifecycle-v2

printf '%s\n' 'Workflow imported and published: Aegis Autonomous Incident Lifecycle.'
