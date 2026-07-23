#!/usr/bin/env bash
set -euo pipefail
fixture="${1:?usage: replay-fixtures.sh <fixture-id>}"
curl -fsS "http://localhost:8081/api/v1/evaluation/replays/${fixture}" -H "Authorization: Bearer ${AEGIS_OPERATOR_TOKEN:?AEGIS_OPERATOR_TOKEN must be set}"
