#!/usr/bin/env bash
set -euo pipefail

docker compose exec -T n8n n8n import:workflow \
  --input=/opt/aegis/workflows/aegis-autonomous-sre.json

docker compose exec -T n8n n8n publish:workflow \
  --id=aegis-autonomous-lifecycle-v2

printf '%s\n' 'Workflow imported and published: Aegis Autonomous Incident Lifecycle.'
