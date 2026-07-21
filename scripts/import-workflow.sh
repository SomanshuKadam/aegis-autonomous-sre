#!/usr/bin/env bash
set -euo pipefail

docker compose exec -T n8n n8n import:workflow \
  --input=/opt/aegis/workflows/aegis-autonomous-sre.json

printf '%s\n' 'Workflow imported. Open http://localhost:5678, open "Aegis - Autonomous SRE Pipeline", and switch it Active.'
