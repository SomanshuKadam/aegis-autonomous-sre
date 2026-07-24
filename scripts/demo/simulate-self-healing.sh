#!/usr/bin/env bash
set -euo pipefail

scenario="${1:-catalog}"
case "$scenario" in
  catalog|inventory|backlog) ;;
  *)
    printf 'usage: %s catalog|inventory|backlog\n' "$0" >&2
    exit 64
    ;;
esac

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_dir"

docker compose cp scripts/demo/simulate-self-healing.py api:/tmp/simulate-self-healing.py >/dev/null
docker compose exec -T api python /tmp/simulate-self-healing.py "$scenario"
