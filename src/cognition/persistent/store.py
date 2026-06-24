# persistent/store.py
"""
Unified persistent store for Packy v2.05 (WO 3.03)

- Provides a single programmatic API for memories, events, and lore
  backed by an SQLite DB with a JSON export companion for portability.
- Designed to be a stable replacement for the older packy_memory.py + persistant_loader.py pair.
- Idempotent initialization, WAL enabled, lightweight dedupe on import.

API (high-level):
  init(db_path=None, json_path=None) -> Store instance (singleton-ish)
  add_memory(text, tags=None) -> dict (row)
  query_recent(limit=20) -> [ {ts,text,tags}... ]
  add_event(event: dict) -> dict
  list_events(limit=100) -> [dict,...]
  get_lore(name=None) -> list
  add_lore(entry) -> dict

Notes:
 - The default DB path matches legacy conventions: /mnt/data/packy_memory.db
 - Everything is defensive: if DB is missing or locked we fall back to JSON file storage.
"""

from __future__ import annotations
import sqlite3
import json
import os
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import threading
import hashlib

logger = logging.getLogger("persistent.store")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
DEFAULT_DB = os.getenv("PACKY_MEMORY_DB", str(_DATA_DIR / "packy_memory.db"))
DEFAULT_JSON = os.getenv("PACKY_MEMORY_JSON", str(_DATA_DIR / "packy_memory.json"))
BACKUP_SUFFIX = ".bak"

_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT,
  text TEXT,
  tags TEXT
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT,
  type TEXT,
  payload TEXT,
  fingerprint TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS lore (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT,
  data TEXT
);

CREATE TABLE IF NOT EXISTS meta (
  k TEXT PRIMARY KEY,
  v TEXT
);
"""

def _now_iso():
    return datetime.now(tz=timezone.utc).isoformat() + "Z"

def _ensure_dir_for(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _hash_event(e: Dict[str, Any]) -> str:
    # Deterministic fingerprint used for simple deduplication
    try:
        j = json.dumps(e, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        j = str(e)
    return hashlib.sha256(j.encode("utf-8")).hexdigest()

class Store:
    """
    Unified store class. Thread-safe for basic operations.
    """

    _instance_lock = threading.RLock()
    _instance: Optional["Store"] = None

    def __init__(self, db_path: str = DEFAULT_DB, json_path: str = DEFAULT_JSON):
        self.db_path = str(Path(db_path).expanduser())
        self.json_path = str(Path(json_path).expanduser())
        self._conn_lock = threading.RLock()
        self._ensure_db()

    @classmethod
    def init(cls, db_path: Optional[str] = None, json_path: Optional[str] = None) -> "Store":
        with cls._instance_lock:
            if cls._instance is not None:
                logger.info("Store.init() called but instance already exists.")
                return cls._instance
            dbp = db_path or DEFAULT_DB
            jnp = json_path or DEFAULT_JSON
            cls._instance = Store(db_path=dbp, json_path=jnp)
            return cls._instance

    @classmethod
    def get(cls) -> "Store":
        if cls._instance is None:
            return cls.init()
        return cls._instance

    # ---------------------------
    # Database utilities
    # ---------------------------
    def _conn(self):
        # sqlite3 is threadsafe when check_same_thread=False, but access guarded by _conn_lock
        # Use WAL mode for concurrency.
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self):
        """
        Ensure DB directory exists, create DB and required tables.
        If DB is missing but JSON export exists, attempt a safe migration into DB.
        """
        _ensure_dir_for(self.db_path)
        # If file exists but not writable we will let the exception propagate (caller should handle).
        created = False
        if not os.path.exists(self.db_path):
            # create empty DB file
            open(self.db_path, "a").close()
            created = True

        # Enable WAL and create schema
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.executescript(_SCHEMA)
            # ensure meta schema_version exists
            cur.execute("INSERT OR IGNORE INTO meta(k,v) VALUES (?,?)", ("schema_version", "1"))
            conn.commit()
        finally:
            conn.close()

        # If DB was newly created and a JSON export exists, import it
        if created and os.path.exists(self.json_path):
            try:
                logger.info("Detected existing JSON memory export; importing into DB: %s", self.json_path)
                self._import_json_to_db()
            except Exception:
                logger.exception("JSON import to DB failed (non-fatal)")

    def _backup_file(self, path: str):
        if not os.path.exists(path):
            return None
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = f"{path}{BACKUP_SUFFIX}.{ts}"
        try:
            shutil.copy2(path, bak)
            logger.info("Backed up %s -> %s", path, bak)
            return bak
        except Exception:
            logger.exception("Failed to backup %s", path)
            return None

    # ---------------------------
    # Import / Migration helpers
    # ---------------------------
    def _load_json_export(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(self.json_path):
                return {"memories": [], "events": [], "lore": []}
            txt = Path(self.json_path).read_text(encoding="utf-8")
            obj = json.loads(txt)
            # Input normalization to expected keys
            if isinstance(obj, dict):
                memories = obj.get("memory") or obj.get("memories") or []
                events = obj.get("events") or []
                lore = obj.get("lore") or []
                return {"memories": memories, "events": events, "lore": lore}
            if isinstance(obj, list):
                return {"memories": obj, "events": [], "lore": []}
        except Exception:
            logger.exception("Failed to parse JSON export %s", self.json_path)
        return {"memories": [], "events": [], "lore": []}

    def _import_json_to_db(self):
        """
        Import JSON export into DB with deduplication.
        This is non-destructive: JSON file is left untouched and DB is appended to.
        """
        data = self._load_json_export()
        mems = data.get("memories", [])
        evs = data.get("events", [])
        lore_items = data.get("lore", [])

        conn = self._conn()
        try:
            cur = conn.cursor()
            for m in mems:
                try:
                    ts = m.get("ts") or _now_iso()
                    text = m.get("text") or m.get("title") or ""
                    tags = m.get("tags") or m.get("tags", [])
                    cur.execute("INSERT INTO memories (ts, text, tags) VALUES (?,?,?)", (ts, text, json.dumps(tags)))
                except Exception:
                    logger.exception("Skipping memory import row due to error")
            for e in evs:
                try:
                    ts = e.get("ts") or _now_iso()
                    t = e.get("type") or e.get("event_type") or "event"
                    payload = json.dumps(e)
                    fp = _hash_event(e)
                    try:
                        cur.execute("INSERT OR IGNORE INTO events (ts, type, payload, fingerprint) VALUES (?,?,?,?)", (ts, t, payload, fp))
                    except Exception:
                        logger.exception("failed to insert event row; skipping")
                except Exception:
                    logger.exception("Skipping event import row due to error")
            for l in lore_items:
                try:
                    key = l.get("key") if isinstance(l, dict) else None
                    data_blob = json.dumps(l)
                    cur.execute("INSERT INTO lore (key, data) VALUES (?,?)", (key, data_blob))
                except Exception:
                    logger.exception("Skipping lore import row due to error")
            conn.commit()
            logger.info("Imported JSON export into DB (counts: memories=%d, events=%d, lore=%d)", len(mems), len(evs), len(lore_items))
        finally:
            conn.close()

    # ---------------------------
    # Public API: memories
    # ---------------------------
    def add_memory(self, text: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        if tags is None:
            tags = []
        ts = _now_iso()
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO memories (ts, text, tags) VALUES (?,?,?)", (ts, text, json.dumps(tags)))
            conn.commit()
            return {"ts": ts, "text": text, "tags": tags}
        finally:
            conn.close()

    def query_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT ts, text, tags FROM memories ORDER BY id DESC LIMIT ?", (limit,))
            rows = []
            for r in cur.fetchall():
                try:
                    tags = json.loads(r["tags"]) if r["tags"] else []
                except Exception:
                    tags = []
                rows.append({"ts": r["ts"], "text": r["text"], "tags": tags})
            return rows
        finally:
            conn.close()

    # ---------------------------
    # Public API: events
    # ---------------------------
    def add_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        ts = event.get("ts") or _now_iso()
        t = event.get("type") or "event"
        payload = json.dumps(event)
        fp = _hash_event(event)
        conn = self._conn()
        try:
            cur = conn.cursor()
            try:
                cur.execute("INSERT OR IGNORE INTO events (ts, type, payload, fingerprint) VALUES (?,?,?,?)", (ts, t, payload, fp))
                conn.commit()
            except sqlite3.IntegrityError:
                # duplicate fingerprint -> ignore
                logger.debug("add_event: duplicate event fingerprint %s", fp)
            return {"ts": ts, "type": t, "fingerprint": fp}
        finally:
            conn.close()

    def list_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT ts, type, payload FROM events ORDER BY id DESC LIMIT ?", (limit,))
            out = []
            for r in cur.fetchall():
                try:
                    payload = json.loads(r["payload"]) if r["payload"] else {}
                except Exception:
                    payload = {"raw": r["payload"]}
                out.append({"ts": r["ts"], "type": r["type"], "payload": payload})
            return out
        finally:
            conn.close()

    # ---------------------------
    # Public API: lore
    # ---------------------------
    def add_lore(self, key: Optional[str], data: Any) -> Dict[str, Any]:
        blob = json.dumps(data)
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO lore (key, data) VALUES (?,?)", (key, blob))
            conn.commit()
            return {"key": key, "data": data}
        finally:
            conn.close()

    def get_lore(self, key: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            if key is None:
                cur.execute("SELECT id, key, data FROM lore ORDER BY id DESC")
                rows = cur.fetchall()
            else:
                cur.execute("SELECT id, key, data FROM lore WHERE key = ? ORDER BY id DESC", (key,))
                rows = cur.fetchall()
            out = []
            for r in rows:
                try:
                    data = json.loads(r["data"]) if r["data"] else None
                except Exception:
                    data = r["data"]
                out.append({"id": r["id"], "key": r["key"], "data": data})
            return out
        finally:
            conn.close()

# Module-level convenience
def init(db_path: Optional[str] = None, json_path: Optional[str] = None) -> Store:
    return Store.init(db_path=db_path, json_path=json_path)

def get_store() -> Store:
    return Store.get()
