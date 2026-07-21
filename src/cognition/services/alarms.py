"""
services.alarms — Alarms API wrapper for Packy.

CRUD functions returning canonical JSON-shaped dicts:
  - create_alarm(...) -> {"ok": True, "alarm": {...}}
  - list_alarms() -> {"ok": True, "alarms": [...]}
  - get_alarm(alarm_id) -> {"ok": True, "alarm": {...}}
  - delete_alarm(alarm_id) -> {"ok": True} / {"ok": False, "error": "..."}

Requires init_persistence() to be called on startup.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("packy.alarms")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

_scheduler_store = None  # type: Optional[Any]


def _ensure_store():
    global _scheduler_store
    if _scheduler_store is None:
        from .main import init_persistence

        _scheduler_store = init_persistence()
    return _scheduler_store


def create_alarm(
    title: str,
    time_iso: str,
    payload: Optional[Dict[str, Any]] = None,
    enabled: bool = True,
) -> Dict[str, Any]:
    """Create an alarm and schedule it. Returns canonical response dict."""
    store = _ensure_store()
    try:
        alarm = store.create_alarm(
            title=title, time_iso=time_iso, payload=payload or {}, enabled=enabled
        )
        return {"ok": True, "alarm": alarm}
    except Exception as e:
        logger.exception("create_alarm failed: %s", e)
        return {"ok": False, "error": str(e)}


def list_alarms() -> Dict[str, Any]:
    """Return all alarms in canonical shape."""
    try:
        store = _ensure_store()
    except Exception as e:
        logger.exception("persistence unavailable in list_alarms: %s", e)
        return {"ok": False, "error": "persistence_unavailable", "alarms": []}
    try:
        alarms = store.list_alarms()
        return {"ok": True, "alarms": alarms}
    except Exception as e:
        logger.exception("list_alarms failed: %s", e)
        return {"ok": False, "error": str(e), "alarms": []}


def get_alarm(alarm_id: int) -> Dict[str, Any]:
    try:
        store = _ensure_store()
        for a in store.list_alarms():
            if int(a["id"]) == int(alarm_id):
                return {"ok": True, "alarm": a}
        return {"ok": False, "error": "not_found"}
    except Exception as e:
        logger.exception("get_alarm error: %s", e)
        return {"ok": False, "error": str(e)}


def delete_alarm(alarm_id: int) -> Dict[str, Any]:
    try:
        store = _ensure_store()
        if store.delete_alarm(int(alarm_id)):
            return {"ok": True}
        return {"ok": False, "error": "not_found"}
    except Exception as e:
        logger.exception("delete_alarm error: %s", e)
        return {"ok": False, "error": str(e)}
