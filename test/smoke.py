#!/usr/bin/env python3
"""Smoke test: verify packy_endpoint imports without NameError."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    import importlib

    importlib.import_module("src.orchestration.packy_endpoint")
    print("ok")
    sys.exit(0)
except NameError as e:
    print(f"NameError: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)
