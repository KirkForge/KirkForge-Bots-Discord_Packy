"""
alarm_routes.py — FastAPI sub-router for alarms, reminders, and scheduler.

Mounts under the main Packy endpoint app via:
    app.include_router(alarm_router, prefix="/alarms")
    app.include_router(alarm_router, prefix="/reminders")

Requires init_persistence() to be called on app startup.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.cognition.services.alarms import create_alarm, list_alarms, get_alarm, delete_alarm
from src.cognition.services.reminders import create_reminder, list_reminders, delete_reminder
from src.cognition.services.scheduler import get_global_scheduler

logger = logging.getLogger("packy.alarm_routes")

alarm_router = APIRouter(tags=["alarms"])
reminder_router = APIRouter(tags=["reminders"])


# ---- Request/Response models ----

class AlarmCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    time_iso: str = Field(..., description="ISO 8601 datetime string")
    payload: Optional[Dict[str, Any]] = None
    enabled: bool = True


class ReminderCreateRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=500)
    time_iso: str = Field(..., description="ISO 8601 datetime string")
    payload: Optional[Dict[str, Any]] = None
    enabled: bool = True


class AlarmResponse(BaseModel):
    ok: bool
    alarm: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AlarmsListResponse(BaseModel):
    ok: bool
    alarms: List[Dict[str, Any]] = []
    error: Optional[str] = None


class ReminderResponse(BaseModel):
    ok: bool
    reminder: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RemindersListResponse(BaseModel):
    ok: bool
    reminders: List[Dict[str, Any]] = []
    error: Optional[str] = None


class DeleteResponse(BaseModel):
    ok: bool
    error: Optional[str] = None


# ---- Alarm routes ----

@alarm_router.post("/", response_model=AlarmResponse)
def api_create_alarm(request: AlarmCreateRequest) -> AlarmResponse:
    """Create a new alarm."""
    result = create_alarm(
        title=request.title,
        time_iso=request.time_iso,
        payload=request.payload,
        enabled=request.enabled,
    )
    return AlarmResponse(**result)


@alarm_router.get("/", response_model=AlarmsListResponse)
def api_list_alarms() -> AlarmsListResponse:
    """List all alarms."""
    result = list_alarms()
    return AlarmsListResponse(**result)


@alarm_router.get("/{alarm_id}", response_model=AlarmResponse)
def api_get_alarm(alarm_id: int) -> AlarmResponse:
    """Get a specific alarm by ID."""
    result = get_alarm(alarm_id)
    return AlarmResponse(**result)


@alarm_router.delete("/{alarm_id}", response_model=DeleteResponse)
def api_delete_alarm(alarm_id: int) -> DeleteResponse:
    """Delete an alarm by ID."""
    result = delete_alarm(alarm_id)
    return DeleteResponse(**result)


# ---- Reminder routes ----

@reminder_router.post("/", response_model=ReminderResponse)
def api_create_reminder(request: ReminderCreateRequest) -> ReminderResponse:
    """Create a new reminder."""
    result = create_reminder(
        note=request.note,
        time_iso=request.time_iso,
        payload=request.payload,
        enabled=request.enabled,
    )
    return ReminderResponse(**result)


@reminder_router.get("/", response_model=RemindersListResponse)
def api_list_reminders() -> RemindersListResponse:
    """List all reminders."""
    result = list_reminders()
    return RemindersListResponse(**result)


@reminder_router.delete("/{reminder_id}", response_model=DeleteResponse)
def api_delete_reminder(reminder_id: int) -> DeleteResponse:
    """Delete a reminder by ID."""
    result = delete_reminder(reminder_id)
    return DeleteResponse(**result)


# ---- Scheduler status route ----

scheduler_router = APIRouter(tags=["scheduler"])


class SchedulerStatusResponse(BaseModel):
    running: bool
    pending_jobs: int
    poll_interval: float


@scheduler_router.get("/status", response_model=SchedulerStatusResponse)
def api_scheduler_status() -> SchedulerStatusResponse:
    """Get scheduler status."""
    try:
        scheduler = get_global_scheduler()
        pending = scheduler.get_pending()
        return SchedulerStatusResponse(
            running=True,
            pending_jobs=len(pending),
            poll_interval=scheduler.poll_interval_seconds,
        )
    except Exception as e:
        logger.exception("scheduler status failed: %s", e)
        return SchedulerStatusResponse(running=False, pending_jobs=0, poll_interval=0)
