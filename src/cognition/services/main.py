"""
services.main — Packy runtime bootstrap (non-blocking).

Creates a global scheduler and exposes helper functions:
 - get_scheduler() -> Scheduler
 - init_persistence(db_path=None) -> SchedulerStore instance
 - shutdown() -> stop scheduler (optional cleanup)

Safe to import under uvicorn/FastAPI. Does NOT block on import.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .scheduler import Scheduler, get_global_scheduler
from .scheduler_store import SchedulerStore

logger = logging.getLogger("packy.main")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

DEFAULT_SCHEDULER_DB = os.getenv("PACKY_SCHEDULER_DB", "/mnt/data/scheduler.db")

_global_scheduler = get_global_scheduler(
    poll_interval_seconds=float(os.getenv("PACKY_SCHEDULER_POLL", "1.0"))
)
logger.info(
    "Global scheduler instance created and started (poll_interval=%s)",
    os.getenv("PACKY_SCHEDULER_POLL", "1.0"),
)

_persistence_store: Optional[SchedulerStore] = None


def get_scheduler() -> Scheduler:
    """Return the global scheduler instance (started)."""
    return _global_scheduler


def init_persistence(db_path: Optional[str] = None) -> SchedulerStore:
    """
    Initialize the persistence layer. Idempotent.

    Should be called by FastAPI startup event or CLI entry point.
    """
    global _persistence_store
    if _persistence_store is not None:
        logger.info("init_persistence() called but persistence already initialized.")
        return _persistence_store

    db_path = db_path or DEFAULT_SCHEDULER_DB
    logger.info("Initializing persistence store at %s", db_path)
    try:
        store = SchedulerStore(scheduler=_global_scheduler, db_path=db_path)
        try:
            store.load_and_schedule_all()
            logger.info("Loaded and scheduled existing alarms/reminders from DB.")
        except Exception as e:
            logger.warning("Failed to load_and_schedule_all() (continuing): %s", e)
        _persistence_store = store
        return _persistence_store
    except Exception as e:
        logger.exception("Failed to initialize persistence store: %s", e)
        raise


def shutdown() -> None:
    """Stop the scheduler and clean up. Safe to call at process exit."""
    global _global_scheduler
    try:
        if _global_scheduler:
            logger.info("Shutting down global scheduler.")
            _global_scheduler.stop()
    except Exception as e:
        logger.exception("Error while shutting down scheduler: %s", e)
