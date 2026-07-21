"""
services.reminders — Minimal reminders API (compat with frontend).

Mirrors alarms behavior and uses the same SchedulerStore table.
Returns canonical shapes:
 - create_reminder(...) -> {"ok": True, "reminder": {...}}
 - list_reminders() -> {"ok": True, "reminders": [...]}
 - delete_reminder(id) -> {"ok": True} / {"ok": False}
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("packy.reminders")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

_scheduler_store = None  # type: Optional[Any]


def _ensure_store():
    global _scheduler_store
    if _scheduler_store is None:
        from .main import init_persistence

        _scheduler_store = init_persistence()
    return _scheduler_store


def create_reminder(
    note: str,
    time_iso: str,
    payload: Optional[Dict[str, Any]] = None,
    enabled: bool = True,
) -> Dict[str, Any]:
    """Create a reminder (mirrors alarm fields, uses 'note' as main text)."""
    store = _ensure_store()
    title = note if note else "Reminder"
    try:
        alarm = store.create_alarm(
            title=title, time_iso=time_iso, payload=payload or {}, enabled=enabled
        )
        return {"ok": True, "reminder": alarm}
    except Exception as e:
        logger.exception("create_reminder failed: %s", e)
        return {"ok": False, "error": str(e)}


def list_reminders() -> Dict[str, Any]:
    try:
        store = _ensure_store()
    except Exception as e:
        logger.exception("persistence unavailable in list_reminders: %s", e)
        return {"ok": False, "error": "persistence_unavailable", "reminders": []}
    try:
        alarms = store.list_alarms()
        reminders = []
        for a in alarms:
            r = a.copy()
            r["note"] = r.get("title")
            reminders.append(r)
        return {"ok": True, "reminders": reminders}
    except Exception as e:
        logger.exception("list_reminders failed: %s", e)
        return {"ok": False, "error": str(e), "reminders": []}


def delete_reminder(reminder_id: int) -> Dict[str, Any]:
    try:
        store = _ensure_store()
        if store.delete_alarm(int(reminder_id)):
            return {"ok": True}
        return {"ok": False, "error": "not_found"}
    except Exception as e:
        logger.exception("delete_reminder error: %s", e)
        return {"ok": False, "error": str(e)}
