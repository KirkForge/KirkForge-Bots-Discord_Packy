"""
services.scheduler_store — Persistence adapter for alarms/reminders.

Uses SQLite with WAL mode for concurrent safety. Delegates alarm firing
to an optional actions module. Idempotent initialization.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .scheduler import Scheduler

logger = logging.getLogger("scheduler_store")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

DEFAULT_DB = os.getenv("PACKY_SCHEDULER_DB", "/mnt/data/scheduler.db")

SCHEMA_VERSION = 1

_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS meta (
    k TEXT PRIMARY KEY,
    v TEXT
);
CREATE TABLE IF NOT EXISTS alarms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    time_iso TEXT,
    payload TEXT,
    enabled INTEGER DEFAULT 1,
    created_ts TEXT,
    updated_ts TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    alarm_id INTEGER,
    next_run_iso TEXT,
    repeat_seconds INTEGER,
    meta TEXT,
    FOREIGN KEY(alarm_id) REFERENCES alarms(id) ON DELETE CASCADE
);
"""


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")


class SchedulerStore:
    """SQLite-backed persistence for the Scheduler."""

    def __init__(self, scheduler: Scheduler, db_path: str = DEFAULT_DB) -> None:
        self.scheduler = scheduler
        self.db_path = db_path
        self._conn_lock = threading.RLock()
        self._ensure_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.executescript(_SCHEMA)
            cur.execute(
                "INSERT OR IGNORE INTO meta(k,v) VALUES (?,?)",
                ("schema_version", str(SCHEMA_VERSION)),
            )
            conn.commit()
        finally:
            conn.close()

    # --- Alarms CRUD -----------------------------------------------------------

    def create_alarm(
        self,
        title: str,
        time_iso: str,
        payload: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        payload_json = json.dumps(payload or {})
        now = _now_iso()
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO alarms (title, time_iso, payload, enabled, created_ts, updated_ts) "
                "VALUES (?,?,?,?,?,?)",
                (title, time_iso, payload_json, 1 if enabled else 0, now, now),
            )
            alarm_id = cur.lastrowid
            conn.commit()
        finally:
            conn.close()

        job_id = self._schedule_alarm_row(alarm_id, title, time_iso, payload or {}, enabled)

        return {
            "id": alarm_id,
            "title": title,
            "time_iso": time_iso,
            "payload": payload or {},
            "enabled": 1 if enabled else 0,
            "job_id": job_id,
        }

    def _schedule_alarm_row(
        self,
        alarm_id: int,
        title: str,
        time_iso: str,
        payload: Dict[str, Any],
        enabled: bool,
    ) -> Optional[str]:
        if not enabled:
            return None

        def _alarm_callback(alarm_id: int = alarm_id) -> None:
            try:
                alarm_row = None
                conn = self._conn()
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT a.*, j.job_id, j.next_run_iso, j.repeat_seconds, j.meta as job_meta "
                        "FROM alarms a LEFT JOIN jobs j ON a.id=j.alarm_id WHERE a.id = ?",
                        (alarm_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        alarm_row = dict(row)
                finally:
                    conn.close()

                if not alarm_row:
                    logger.info("[scheduler_store] Alarm %s not found in DB (deleted?)", alarm_id)
                    return

                logger.info(
                    "[scheduler_store] Alarm fired alarm_id=%s title=%s",
                    alarm_id,
                    alarm_row.get("title"),
                )

                # Try to forward event
                try:
                    from .integration import forward_event

                    forward_event(alarm_row)
                except Exception:
                    logger.debug("[scheduler_store] forward_event unavailable")

            except Exception:
                logger.exception("[scheduler_store] Alarm callback error (ignored)")

        job_id = self.scheduler.schedule_at(
            time_iso, _alarm_callback, meta={"alarm_id": alarm_id, "title": title}
        )

        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO jobs (job_id, alarm_id, next_run_iso, repeat_seconds, meta) "
                "VALUES (?,?,?,?,?)",
                (job_id, alarm_id, time_iso, None, json.dumps({"title": title})),
            )
            conn.commit()
        finally:
            conn.close()
        return job_id

    def _delete_job_mapping_by_alarm(self, alarm_id: int) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT job_id FROM jobs WHERE alarm_id = ?", (alarm_id,))
            row = cur.fetchone()
            if row:
                job_id = row["job_id"]
                try:
                    self.scheduler.cancel(job_id)
                except Exception:
                    logger.exception("scheduler.cancel failed for job %s", job_id)
                cur.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
                conn.commit()
        finally:
            conn.close()

    def delete_alarm(self, alarm_id: int) -> bool:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM alarms WHERE id = ?", (alarm_id,))
            if not cur.fetchone():
                return False
            self._delete_job_mapping_by_alarm(alarm_id)
            cur.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    def list_alarms(self) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT a.*, j.job_id, j.next_run_iso, j.repeat_seconds, j.meta as job_meta "
                "FROM alarms a LEFT JOIN jobs j ON a.id=j.alarm_id ORDER BY a.id ASC"
            )
            rows = cur.fetchall()
            out: List[Dict[str, Any]] = []
            for r in rows:
                payload: Dict[str, Any] = {}
                try:
                    payload = json.loads(r["payload"]) if r["payload"] else {}
                except Exception:
                    payload = {"_raw": r["payload"]}
                job_meta: Dict[str, Any] = {}
                try:
                    job_meta = json.loads(r["job_meta"]) if r["job_meta"] else {}
                except Exception:
                    job_meta = {}
                out.append(
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "time_iso": r["time_iso"],
                        "payload": payload,
                        "enabled": r["enabled"],
                        "job_id": r["job_id"],
                        "next_run_iso": r["next_run_iso"],
                        "repeat_seconds": r["repeat_seconds"],
                        "job_meta": job_meta,
                    }
                )
            return out
        finally:
            conn.close()

    def load_and_schedule_all(self) -> None:
        """Idempotently load alarms from DB and schedule them."""
        alarms = self.list_alarms()
        for a in alarms:
            job_id = a.get("job_id")
            need_schedule = True
            if job_id:
                pending = {j["job_id"] for j in (self.scheduler.get_pending() or [])}
                if job_id in pending:
                    need_schedule = False
            if need_schedule and a["enabled"]:
                self._schedule_alarm_row(
                    a["id"], a["title"], a["time_iso"], a["payload"] or {}, bool(a["enabled"])
                )

    def get_schema_version(self) -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT v FROM meta WHERE k='schema_version'")
            r = cur.fetchone()
            return int(r["v"]) if r else 0
        finally:
            conn.close()

    def set_schema_version(self, v: int) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO meta(k,v) VALUES (?,?)", ("schema_version", str(v)))
            conn.commit()
        finally:
            conn.close()
