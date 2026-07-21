"""
services.google.google_calendar — Google Calendar event retrieval.

Requires google_services credentials to be configured.
"""

from __future__ import annotations

import datetime
import logging
from typing import Dict, List

from .google_services import get_calendar_service

logger = logging.getLogger("packy.google_calendar")


def get_today_events() -> List[Dict]:
    """Get today's calendar events."""
    svc = get_calendar_service()
    if svc is None:
        return []
    now = datetime.datetime.utcnow().isoformat() + "Z"
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat() + "Z"
    try:
        events = (
            svc.events()
            .list(
                calendarId="primary",
                timeMin=now,
                timeMax=end,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
            .get("items", [])
        )
        return _format_events(events)
    except Exception as e:
        logger.exception("get_today_events failed: %s", e)
        return []


def get_week_events() -> List[Dict]:
    """Get this week's calendar events."""
    svc = get_calendar_service()
    if svc is None:
        return []
    now = datetime.datetime.utcnow().isoformat() + "Z"
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + "Z"
    try:
        events = (
            svc.events()
            .list(
                calendarId="primary",
                timeMin=now,
                timeMax=end,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
            .get("items", [])
        )
        return _format_events(events)
    except Exception as e:
        logger.exception("get_week_events failed: %s", e)
        return []


def _format_events(events: list) -> List[Dict]:
    formatted = []
    for e in events:
        formatted.append(
            {
                "title": e.get("summary", "(no title)"),
                "start": e["start"].get("dateTime", e["start"].get("date")),
                "end": e["end"].get("dateTime", e["end"].get("date")),
                "location": e.get("location"),
                "id": e.get("id"),
            }
        )
    return formatted
