# persistent/migrate_store.py
"""
Safe migration assistant for persistent/store.py

Usage (interactive):
  python3 persistent/migrate_store.py

Behavior:
 - Ensures DB directory exists
 - Backs up existing DB and JSON export to .bak.TIMESTAMP
 - Enables WAL mode and ensures schema
 - Imports JSON exports (if present) into the DB with deduplication
 - Idempotent: safe to re-run
"""

from __future__ import annotations
import argparse
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import sqlite3
import shutil

# Use the unified store implementation
try:
    from persistent.store import init as store_init, get_store
except Exception:
    # If the store module is not importable, attempt to import local path
    # and adjust sys.path
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here.parent))
    from persistent.store import init as store_init, get_store

logger = logging.getLogger("persistent.migrate_store")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

def _backup(path: Path):
    if not path.exists():
        return None
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = path.with_name(path.name + ".bak." + ts)
    try:
        shutil.copy2(str(path), str(dest))
        logger.info("Backed up %s -> %s", path, dest)
        return dest
    except Exception:
        logger.exception("Backup failed for %s", path)
        return None

def run_migration(db_path: str, json_path: str):
    dbp = Path(db_path)
    jnp = Path(json_path)

    # Ensure parent dirs
    if dbp.parent and not dbp.parent.exists():
        dbp.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Created directory %s", dbp.parent)

    # Backups
    _backup(dbp)
    _backup(jnp)

    # Initialize store (creates DB and schema if missing)
    try:
        store = store_init(db_path=db_path, json_path=json_path)
        logger.info("Store initialized at db=%s json=%s", db_path, json_path)
    except Exception as e:
        logger.exception("Failed to initialize unified store: %s", e)
        raise

    # Attempt to import JSON export into DB (store will attempt on creation,
    # but expose a helper via get_store())
    try:
        s = get_store()
        # if JSON export exists and DB was pre-existing but missing data,
        # call private import (safe; dedupes)
        # The store class exposes _import_json_to_db() internally — call it if available.
        if hasattr(s, "_import_json_to_db"):
            try:
                s._import_json_to_db()
                logger.info("Successfully ran JSON->DB import routine.")
            except Exception:
                logger.exception("JSON->DB import failed (non-fatal).")
        else:
            logger.info("Store missing import helper; skipping JSON import.")
    except Exception:
        logger.exception("Post-init import step failed.")

    logger.info("Migration completed. Please restart backend to pick up changes.")

def main():
    _data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
    _default_db = os.getenv("PACKY_MEMORY_DB", str(_data_dir / "packy_memory.db"))
    _default_json = os.getenv("PACKY_MEMORY_JSON", str(_data_dir / "packy_memory.json"))
    parser = argparse.ArgumentParser(description="Migrate persistent JSON memory exports into unified SQLite store.")
    parser.add_argument("--db", default=_default_db, help="Target DB path")
    parser.add_argument("--json", default=_default_json, help="Source JSON export path")
    args = parser.parse_args()

    run_migration(db_path=args.db, json_path=args.json)

if __name__ == "__main__":
    main()
