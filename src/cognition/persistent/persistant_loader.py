"""
persistant_loader.py — Packy v2.05 Persistent Memory Loader (FIXED)

This loader:
 - Loads Packy's JSON-based memory (packy_memory.json)
 - Loads Packy's event logs (packy_events.json)
 - Attempts to load persistent_lore if present, but does NOT require it
 - Normalizes all entries into a single structure:
       {
         "memories": [...],
         "events": [...],
         "lore": [...]
       }
 - Designed to be wrapped by MemoryAdapter and used by PackyBrain.

Compatible with:
   - persistent/packy_memory.py (SQLite + JSON hybrid)
   - persistent/memory_adapter.py
"""

from __future__ import annotations
import json
from pathlib import Path

# Resolve paths relative to this file so they work regardless of CWD
_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

MEMORY_FILE = _DATA_DIR / "packy_memory.json"
EVENTS_FILE = _DATA_DIR / "packy_events.json"
PERSISTENT_LORE_FILE = _DATA_DIR / "pending_lore" / "packy_persistent_lore.json"


def _safe_load(path, top_key=None):
    """
    Load a JSON file in flexible format:
      - { "memory": [...] }
      - { "events": [...] }
      - { "lore": [...] }
      - [ ... ]
    Returns [] if missing or invalid.
    """
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(data, dict) and top_key and top_key in data:
        return data.get(top_key, [])

    if isinstance(data, list):
        return data

    # Last fallback: any dict → flatten values that are lists
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
        return []

    return []


def load_all():
    """
    Load all dynamic memory components Packy can use.

    Returns a dictionary:
    {
      "memories": [...],
      "events": [...],
      "lore": [...]
    }

    This structure is safe to pass directly to MemoryAdapter.
    """
    # Load JSON memory
    memories = _safe_load(MEMORY_FILE, "memory")

    # Load events
    events = _safe_load(EVENTS_FILE, "events")

    # Load persistent lore (OPTIONAL)
    # If missing, we simply return an empty lore list.
    lore = _safe_load(PERSISTENT_LORE_FILE, "lore")

    return {
        "memories": memories,
        "events": events,
        "lore": lore,
    }
