"""Shared test configuration for Aegis."""

from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if not APP_ROOT.exists():
    APP_ROOT = PROJECT_ROOT
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DATABASE", "aegis_test")
os.environ.setdefault("AEGIS_ENVIRONMENT", "test")
os.environ.setdefault("AEGIS_ORCHESTRATOR_TOKEN", "test-orchestrator-token")
os.environ.setdefault("AEGIS_OPERATOR_TOKEN", "test-operator-token")
