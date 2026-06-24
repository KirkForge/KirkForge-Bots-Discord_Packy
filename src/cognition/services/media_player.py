"""
services.media_player — Audio playback backend for Packy.

Works with mpv, ffplay, and subprocess fallbacks. Supports local
files, YouTube URLs, and TTS passthrough.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess

logger = logging.getLogger("packy.media_player")

MPV = shutil.which("mpv")
FFPLAY = shutil.which("ffplay")


def _run(cmd: list[str], blocking: bool = False) -> bool:
    """Execute a command safely. If blocking=True, wait for completion."""
    try:
        logger.debug("Executing command: %s", cmd)
        if blocking:
            subprocess.run(cmd, check=True)
        else:
            subprocess.Popen(cmd)
        return True
    except Exception as e:
        logger.exception("Command failed: %s", cmd)
        return False


def play_file(path: str, blocking: bool = False) -> bool:
    """Play an audio file using mpv or ffplay."""
    if not os.path.exists(path):
        logger.error("play_file: file not found: %s", path)
        return False
    if MPV:
        return _run([MPV, "--no-video", "--quiet", path], blocking)
    if FFPLAY:
        return _run([FFPLAY, "-nodisp", "-autoexit", "-loglevel", "quiet", path], blocking)
    logger.error("No audio player found (mpv or ffplay). Cannot play file.")
    return False


def speak_text(text: str, blocking: bool = False) -> bool:
    """Speak text using the TTS engine."""
    try:
        from . import tts_engine
        return tts_engine.speak(text, blocking)
    except Exception as e:
        logger.exception("speak_text failed: %s", e)
        return False


def play_youtube(url: str, blocking: bool = False) -> bool:
    """Play a YouTube URL using mpv. Falls back to logging the URL."""
    if not MPV:
        logger.warning("mpv not available — cannot play YouTube: %s", url)
        return False
    return _run([MPV, "--no-video", "--quiet", url], blocking)


def self_test() -> None:
    """Simple test to confirm mpv/ffplay works."""
    logger.info("[media_player] mpv = %s", MPV)
    logger.info("[media_player] ffplay = %s", FFPLAY)
    if MPV:
        logger.info("mpv detected — OK")
    elif FFPLAY:
        logger.info("ffplay detected — OK")
    else:
        logger.warning("No supported media player found!")
