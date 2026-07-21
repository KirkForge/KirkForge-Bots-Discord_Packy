# persistent/packy_memory.py
"""
Hybrid memory store:
- Primary: SQLite for indexed queries (data/packy_memory.db)
- Secondary: JSON export (data/packy_memory.json) for portability
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
DB_FILE = _DATA_DIR / "packy_memory.db"
JSON_FILE = _DATA_DIR / "packy_memory.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT,
  text TEXT,
  tags TEXT -- JSON encoded list
);
"""


def _conn():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init():
    conn = _conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def add_memory(text, tags=None):
    if tags is None:
        tags = []
    ts = datetime.utcnow().isoformat() + "Z"
    conn = _conn()
    conn.execute(
        "INSERT INTO memories (ts, text, tags) VALUES (?, ?, ?)", (ts, text, json.dumps(tags))
    )
    conn.commit()
    conn.close()
    # also append to JSON export for portability
    _sync_json()
    return {"ts": ts, "text": text, "tags": tags}


def query_recent(limit=20):
    conn = _conn()
    cur = conn.execute("SELECT ts, text, tags FROM memories ORDER BY id DESC LIMIT ?", (limit,))
    rows = [{"ts": r[0], "text": r[1], "tags": json.loads(r[2] or "[]")} for r in cur.fetchall()]
    conn.close()
    return rows


def _sync_json():
    conn = _conn()
    cur = conn.execute("SELECT ts, text, tags FROM memories ORDER BY id ASC")
    allrows = [{"ts": r[0], "text": r[1], "tags": json.loads(r[2] or "[]")} for r in cur.fetchall()]
    conn.close()
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump({"memory": allrows}, f, indent=2)


# initialize on import
init()
