"""
services.actions.alarm_actions — Alarm action pipeline.

Implements the canonical alarm action pipeline:
  1) Build event object
  2) Forward event to integration
  3) Play media (if payload.media)
  4) Speak TTS (if payload.tts_message or payload.tts)
  5) Log completion

Defensive: never raises exceptions that bubble into the scheduler worker.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("alarm_actions")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def run_alarm_action(alarm_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the full alarm action pipeline for a fired alarm.
    """
    result: Dict[str, Any] = {"ok": True, "actions": []}

    # Step 1: Build event
    event = {
        "type": "alarm_fired",
        "alarm_id": alarm_row.get("id"),
        "title": alarm_row.get("title"),
        "time_iso": alarm_row.get("time_iso"),
        "payload": alarm_row.get("payload", {}),
    }

    # Step 2: Forward event
    try:
        from ..integration import forward_event

        forward_event(event)
        result["actions"].append("forward_event")
    except Exception:
        logger.debug("forward_event unavailable")

    # Step 3: Media playback
    payload = alarm_row.get("payload", {}) or {}
    media = payload.get("media")
    if media:
        try:
            from ..media_player import play_file, play_youtube

            if isinstance(media, str) and media.startswith("http"):
                if "youtube" in media or "youtu.be" in media:
                    play_youtube(media)
                else:
                    play_file(media)
            else:
                play_file(media)
            result["actions"].append("media_played")
        except Exception:
            logger.exception("Media playback failed")

    # Step 4: TTS
    tts_text = payload.get("tts_message") or payload.get("tts") or payload.get("text")
    if tts_text:
        try:
            from ..tts_engine import TtsEngine

            engine = TtsEngine()
            engine.speak(tts_text)
            result["actions"].append("tts_spoken")
        except Exception:
            logger.exception("TTS failed")

    logger.info(
        "[alarm_actions] Alarm fired alarm_id=%s title=%s actions=%s",
        alarm_row.get("id"),
        alarm_row.get("title"),
        result["actions"],
    )
    return result
