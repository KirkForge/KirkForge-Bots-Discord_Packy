import json
from pathlib import Path
from datetime import datetime

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PERSISTENT_LORE = _DATA_DIR / "pending_lore" / "packy_persistent_lore.json"

def write_lore(entry_text, tags=None):
    """Append new lore created by Packy himself."""

    if tags is None:
        tags = ["self_written"]

    entry = {
        "text": entry_text,
        "tags": tags,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    # load or create file
    PERSISTENT_LORE.parent.mkdir(parents=True, exist_ok=True)
    if not PERSISTENT_LORE.exists():
        data = {"version": 1, "lore": []}
    else:
        with open(PERSISTENT_LORE, "r", encoding="utf-8") as f:
            data = json.load(f)

    data["lore"].append(entry)

    tmp = PERSISTENT_LORE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.rename(PERSISTENT_LORE)
    return entry
