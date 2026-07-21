"""
services.config_manager — JSON config persistence for Packy.

Uses env var CONFIG_PATH or defaults to /mnt/data/config.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .env import env

CONFIG_PATH = Path(env("CONFIG_PATH", "/mnt/data/config.json"))


def load_config() -> Dict[str, Any]:
    """Load config from disk. Returns empty defaults if file missing."""
    if not CONFIG_PATH.exists():
        return {"alarms": [], "reminders": []}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: Dict[str, Any]) -> None:
    """Persist config to disk atomically."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(CONFIG_PATH) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.flush()
    import os

    os.replace(tmp, str(CONFIG_PATH))
