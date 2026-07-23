#!/usr/bin/env python3
"""Smoke test: verify packy_endpoint imports without NameError."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Auth gate: packy_endpoint refuses to start without PACKY_API_SECRET.
# Set a dummy secret for the smoke test.
if not os.getenv("PACKY_API_SECRET") and not os.getenv("PACKY_DEV_LICENSE"):
    os.environ["PACKY_DEV_LICENSE"] = "1"

try:
    import importlib

    importlib.import_module("src.orchestration.packy_endpoint")
    print("ok")
    sys.exit(0)
except NameError as e:
    print(f"NameError: {e}")
    sys.exit(1)
except SystemExit as e:
    # Re-raise SystemExit from auth/license gates (not from our test)
    if e.code == 0 or e.code is None:
        print("ok")
        sys.exit(0)
    print(f"SystemExit({e.code}) during import — missing env vars?")
    sys.exit(1)
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)
