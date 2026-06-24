"""
services.actions.tts — TTS action handler for Packy.

Provides speak() action that calls the TTS engine.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("actions.tts")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def speak(
    text: str,
    voice: Optional[str] = None,
    blocking: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Speak text via TTS engine. Returns result dict."""
    if not text:
        return {"ok": False, "error": "empty_text"}

    try:
        from ..tts_engine import TtsEngine
        engine = TtsEngine()
        out = engine.speak(text, blocking=bool(blocking))
        if out:
            return {"ok": True, "out": out}
        return {"ok": False, "error": "tts_produced_no_output"}
    except Exception as e:
        logger.exception("TTS speak failed: %s", e)
        return {"ok": False, "error": str(e)}
