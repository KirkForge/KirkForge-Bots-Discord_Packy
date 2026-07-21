"""PackyTtsMixin — TTS parameter helper (rate/pitch/volume).

Extracted from packy_brain.py lines 568-585.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("packy.brain.tts")


class PackyTtsMixin:
    def get_tts_params(self) -> Dict[str, Any]:
        default = {"rate": 150, "pitch": 1.0, "volume": 1.0}
        try:
            params = {}
            params["rate"] = int(self.voice_profile.get("rate", default["rate"]))
            params["pitch"] = float(self.voice_profile.get("pitch", default["pitch"]))
            params["volume"] = float(self.voice_profile.get("volume", default["volume"]))
            if self.mood == "grumpy":
                params["rate"] = max(120, params["rate"] - 10)
            elif self.mood == "cheerful":
                params["rate"] = min(220, params["rate"] + 10)
            return params
        except Exception:
            logger.exception("get_tts_params failed; returning defaults")
            return default
