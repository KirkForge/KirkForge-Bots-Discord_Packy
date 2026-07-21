"""
services.tts_engine — Text-to-speech engine for Packy.

Uses gTTS (Google Text-to-Speech) for generation and local
players (mpg123, ffplay, etc.) for playback.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path

try:
    from gtts import gTTS

    _GTTS_AVAILABLE = True
except ImportError:
    _GTTS_AVAILABLE = False

LOG = logging.getLogger("packy.tts")
LOG.setLevel(logging.INFO)
if not LOG.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    LOG.addHandler(ch)

DEFAULT_AUDIO_DIR = Path(os.getenv("PACKY_TTS_DIR", "/tmp/packy_tts"))


class TtsEngine:
    """gTTS-based TTS with local audio playback."""

    def __init__(self, audio_dir: str | Path = DEFAULT_AUDIO_DIR, provider: str = "gtts") -> None:
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.provider = provider

    def _filename(self) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        uid = uuid.uuid4().hex[:6]
        return str(self.audio_dir / f"tts_{ts}_{uid}.mp3")

    def speak(self, text: str, play_local: bool = False) -> str:
        """Generate TTS audio file. Returns path to the MP3."""
        if not _GTTS_AVAILABLE:
            LOG.warning("gTTS not installed — cannot generate TTS")
            return ""

        path = self._filename()
        LOG.info("Generating TTS file: %s", path)
        tts = gTTS(text=text, lang="en")
        tts.save(path)
        LOG.info("Saved TTS file: %s", path)
        if play_local:
            self._play_local(path)
        return path

    @staticmethod
    def _play_local(path: str) -> None:
        """Try to play audio file using available system players."""

        def _player_thread(p: str) -> None:
            players = [
                ("mpg123", ["mpg123", p]),
                ("mpg321", ["mpg321", p]),
                ("ffplay", ["ffplay", "-nodisp", "-autoexit", p]),
                ("aplay", ["aplay", p]),
                ("paplay", ["paplay", p]),
                ("cvlc", ["cvlc", "--play-and-exit", p]),
            ]
            for name, cmd in players:
                if shutil.which(cmd[0]):
                    LOG.info("Using player %s for %s", name, p)
                    try:
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return
                    except Exception as e:
                        LOG.exception("Failed player %s: %s", name, e)
            LOG.error("No usable audio player found.")

        threading.Thread(target=_player_thread, args=(path,), daemon=True).start()
