"""
services.google.google_services — Google OAuth credential loader.

Loads token.json and provides Calendar/Gmail service builders.
Requires google-auth and google-api-python-client packages.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..env import env

logger = logging.getLogger("packy.google_services")

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False


def load_credentials() -> Optional["Credentials"]:
    """Load Google OAuth token. Auto-refreshes when expired."""
    if not _GOOGLE_AVAILABLE:
        logger.warning("google-auth / google-api-python-client not installed")
        return None

    token_path = env("GOOGLE_TOKEN_FILE")
    creds_path = Path(token_path) if token_path else None

    if not creds_path or not creds_path.exists():
        logger.info("No token.json found. Please authenticate first.")
        return None

    scopes = [s.strip() for s in env("GOOGLE_SCOPES", "").split(",") if s.strip()]
    creds = Credentials.from_authorized_user_file(str(creds_path), scopes=scopes)

    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        try:
            creds.refresh(Request())
            creds_path.write_text(creds.to_json())
        except Exception as e:
            logger.warning("Token refresh failed: %s", e)

    return creds


def get_calendar_service() -> Optional[object]:
    """Build and return a Google Calendar service object."""
    creds = load_credentials()
    if creds is None:
        return None
    try:
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        logger.exception("Calendar service failed: %s", e)
        return None


def get_gmail_service() -> Optional[object]:
    """Build and return a Gmail service object."""
    creds = load_credentials()
    if creds is None:
        return None
    try:
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        logger.exception("Gmail service failed: %s", e)
        return None
