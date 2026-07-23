#!/usr/bin/env bash
set -euo pipefail

# Legacy filename retained for existing local shortcuts. This is a reviewer-operated manual
# catalog walkthrough, not an automated validation flow.
docker compose cp scripts/demo/catalog-auto-recovery-demo.py api:/tmp/catalog-auto-recovery-demo.py
docker compose exec -T api python /tmp/catalog-auto-recovery-demo.py
