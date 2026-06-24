"""
services.env — Environment variable loader for Packy.

Loads .env from multiple candidate paths and provides a safe getter.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

CANDIDATES = [
    Path(".env"),
    Path("/mnt/data/.env"),
    Path(__file__).resolve().parent.parent.parent.parent.parent / ".env",
    Path(__file__).resolve().parent / ".env",
]

_loaded = False
for p in CANDIDATES:
    if p.exists():
        load_dotenv(dotenv_path=str(p), override=False)
        _loaded = True
        break


def env(name: str, default: str | None = None) -> str | None:
    """Safe getter for environment variables with a default."""
    return os.getenv(name, default)
