"""
services.integration — External service integration stubs for Packy.

Provides polling stubs for Google Calendar, Gmail, Weather, and RSS.
Actual implementations require OAuth credentials and API keys.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .env import env

logger = logging.getLogger("packy.integration")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def poll_google_calendar() -> None:
    """Poll Google Calendar for upcoming events (stub — requires OAuth)."""
    creds_file = env("GOOGLE_CREDENTIALS_FILE")
    token_file = env("GOOGLE_TOKEN_FILE")
    if not creds_file or not token_file:
        logger.info("[Calendar] Missing Google OAuth paths in env.")
        return
    logger.info("[Calendar] poll_google_calendar(): credentials present (stub).")


def poll_gmail() -> None:
    """Poll Gmail for unread messages (stub — requires OAuth)."""
    creds_file = env("GOOGLE_CREDENTIALS_FILE")
    token_file = env("GOOGLE_TOKEN_FILE")
    if not creds_file or not token_file:
        logger.info("[Gmail] Missing Google OAuth paths in env.")
        return
    logger.info("[Gmail] poll_gmail(): token present (stub).")


def poll_weather() -> None:
    """Poll weather API (stub — requires API key)."""
    key = env("WEATHER_API_KEY")
    url = env("WEATHER_API_URL", "https://api.openweathermap.org/data/2.5/weather")
    loc = env("WEATHER_DEFAULT_LOCATION", "")
    if not key:
        logger.info("[Weather] Missing WEATHER_API_KEY in env.")
        return
    logger.info("[Weather] poll_weather(): would call %s for %s (stub).", url, loc)


def poll_rss() -> None:
    """Poll RSS feeds (stub — requires RSS_FEEDS env var)."""
    feeds = env("RSS_FEEDS", "")
    if not feeds:
        logger.info("[RSS] No RSS_FEEDS set in env.")
        return
    feed_list = [f.strip() for f in feeds.split(",") if f.strip()]
    if not feed_list:
        logger.info("[RSS] RSS_FEEDS value is empty.")
        return
    logger.info("[RSS] poll_rss(): configured %d feeds (stub).", len(feed_list))


def forward_event(event: Dict[str, Any]) -> None:
    """Forward an event to registered handlers (stub)."""
    logger.info("[Integration] Forwarded event: %s", event.get("title", event))
