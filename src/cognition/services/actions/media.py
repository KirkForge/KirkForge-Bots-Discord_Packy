"""
services.actions.media — Media control actions for Packy.

Provides play(), stop(), pause(), set_volume() action handlers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("actions.media")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def play(descriptor: Dict[str, Any], blocking: bool = False) -> Dict[str, Any]:
    """Play a media item. descriptor can contain 'url' or 'file' keys."""
    if not descriptor:
        return {"ok": False, "played": False, "reason": "empty_descriptor"}

    url = descriptor.get("url")
    file_path = descriptor.get("file") or descriptor.get("path")

    try:
        from ..media_player import play_file, play_youtube

        if url:
            if "youtube" in url or "youtu.be" in url:
                if play_youtube(url, blocking=blocking):
                    return {"ok": True, "played": True, "reason": None}
            else:
                if play_file(url, blocking=blocking):
                    return {"ok": True, "played": True, "reason": None}

        if file_path:
            if play_file(file_path, blocking=blocking):
                return {"ok": True, "played": True, "reason": None}

        return {"ok": False, "played": False, "reason": "unsupported_media_descriptor"}
    except Exception as e:
        logger.exception("play() failed")
        return {"ok": False, "played": False, "reason": str(e)}


def stop() -> Dict[str, Any]:
    return {"ok": True, "note": "stop not yet implemented for background players"}


def pause() -> Dict[str, Any]:
    return {"ok": True, "note": "pause not yet implemented for background players"}


def set_volume(volume: int) -> Dict[str, Any]:
    return {"ok": True, "note": f"Volume control not yet implemented (requested {volume})"}
