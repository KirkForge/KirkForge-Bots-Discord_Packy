import json, os, uuid, datetime
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DEFAULT_PENDING_FOLDER = _DATA_DIR / "pending_lore"

def create_lore_entry(category, subcategory, packy_text, state):
    entry = {
        "id": str(uuid.uuid4()),
        "category": category,
        "subcategory": subcategory,
        "mood": state["mood"],
        "cpu": state["cpu_pct"],
        "temp": state["weather"],
        "text": packy_text.strip(),
        "tags": [],   # can be auto-filled later
        "approved": False,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    return entry

def save_pending_entry(entry, folder=None):
    folder = Path(folder) if folder else _DEFAULT_PENDING_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{entry['id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2)
    return str(path)
