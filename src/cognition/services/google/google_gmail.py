"""
services.google.google_gmail — Gmail unread count and recent messages.

Requires google_services credentials to be configured.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from .google_services import get_gmail_service

logger = logging.getLogger("packy.google_gmail")


def get_unread_count() -> int:
    """Get the number of unread messages in the inbox."""
    svc = get_gmail_service()
    if svc is None:
        return 0
    try:
        res = svc.users().labels().get(userId="me", id="UNREAD").execute()
        return res.get("messagesUnread", 0)
    except Exception as e:
        logger.exception("Unread count failed: %s", e)
        return 0


def get_recent_messages(max_results: int = 10) -> List[Dict]:
    """Get the most recent inbox messages."""
    svc = get_gmail_service()
    if svc is None:
        return []
    try:
        res = (
            svc.users()
            .messages()
            .list(userId="me", maxResults=max_results, labelIds=["INBOX"])
            .execute()
        )
        messages = []
        for m in res.get("messages", []):
            detail = svc.users().messages().get(userId="me", id=m["id"]).execute()
            messages.append(
                {
                    "id": m["id"],
                    "snippet": detail.get("snippet"),
                    "threadId": detail.get("threadId"),
                }
            )
        return messages
    except Exception as e:
        logger.exception("Fetching messages failed: %s", e)
        return []
