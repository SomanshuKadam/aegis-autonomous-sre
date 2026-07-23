#!/usr/bin/env bash
set -euo pipefail

# Reviewer-operated local walkthrough runner. Results are written outside the repository so
# scenario IDs can be handed to an operator without creating generated files to commit.
RESULTS_FILE="${AEGIS_DEMO_RESULTS_FILE:-/tmp/aegis-scenario-results-$(date +%Y%m%d%H%M%S).log}"

run_scenario() {
  local script="$1"
  docker compose cp "scripts/demo/${script}" api:"/tmp/${script}" >/dev/null
  docker compose exec -T api python "/tmp/${script}" | tee -a "$RESULTS_FILE"
}

run_scenario catalog-auto-recovery-demo.py
run_scenario inventory-approval-demo.py
run_scenario backlog-recovery-demo.py
run_scenario backlog-safe-refusal-demo.py

printf 'scenario correlations recorded in %s\n' "$RESULTS_FILE"
