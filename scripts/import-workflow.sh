#!/usr/bin/env bash
set -euo pipefail

docker compose exec -T n8n n8n import:workflow \
  --input=/opt/aegis/workflows/aegis-autonomous-sre.json

printf '%s\n' 'Workflow imported. Verify "Aegis Autonomous Incident Lifecycle" is active at http://localhost:5678.'
