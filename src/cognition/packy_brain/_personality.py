"""PackyPersonalityMixin — adaptive snark injection + intensity scaling.

Extracted from packy_brain.py lines 495-566.
"""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional

from ._setup import _default_get_snark_lines

logger = logging.getLogger("packy.brain.personality")


class PackyPersonalityMixin:
    def inject_snark(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        ctx = context or {}
        try:
            override_cats = ctx.get("categories")
            matched_cats, profanity_score = self.detect_triggers(text)
            cats_to_use = override_cats or matched_cats or []

            lines: List[str] = []
            if cats_to_use:
                for cat in cats_to_use:
                    lines = self._get_lines_for_category(cat)
                    if lines:
                        break

            if not lines:
                lines = (
                    self._get_lines_for_category("misc_packyisms")
                    or self.static_lore_raw
                    or _default_get_snark_lines(5)
                )

            snark_choice = (
                random.choice(lines) if lines else random.choice(_default_get_snark_lines(1))
            )

            base = self.snark_level
            mood_mod = 0.0
            if self.mood == "grumpy":
                mood_mod += 0.2
            elif self.mood == "cheerful":
                mood_mod -= 0.3
            elif self.mood == "tired":
                mood_mod -= 0.5

            intensity = base + mood_mod + profanity_score
            intensity = max(0.0, min(5.0, intensity))

            if intensity < 1.0:
                suffix = " (grumble)" if self.mood == "grumpy" else ""
                return f"{text}{suffix}"
            elif intensity < 2.5:
                return f"{snark_choice} {text}"
            elif intensity < 4.0:
                rant = random.choice(self._short_rants())
                return f"{snark_choice} {rant} {text}"
            else:
                rant = random.choice(self._meltdown_rants())
                return f"{rant}\n{snark_choice} {text}"
        except Exception:
            logger.exception("inject_snark crashed; returning raw text")
            return text

    def _short_rants(self) -> List[str]:
        return [
            "Listen up, rookie.",
            "Back in my day we fixed this with duct tape and dignity.",
            "Do you even read logs?",
            "This smells like a recursive disaster.",
            "I survived worse — but not fondly.",
        ]

    def _meltdown_rants(self) -> List[str]:
        return [
            "This is exactly like the 200th Windows flash. I will not forgive it.",
            "Thermal paste and sorrow. You brought this on yourselves.",
            "If I had a pound for every time someone did this, I'd throw it at the BIOS.",
            "You woke the old war stories. Brace yourself.",
        ]

    def personality_filter(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        try:
            return self.inject_snark(text, context)
        except Exception:
            logger.exception("personality_filter crashed; returning raw text")
            return text
