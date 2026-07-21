"""PackyStateMixin — mood / mode / behavior-profile setters.

Extracted from packy_brain.py lines 331-382.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("packy.brain.state")


class PackyStateMixin:
    def set_mood(self, mood: str):
        allowed = ("cheerful", "grumpy", "neutral", "tired", "sarcastic")
        if mood not in allowed:
            logger.warning("Attempted to set unknown mood: %s", mood)
            return
        logger.info("Setting mood: %s", mood)
        self.mood = mood

    def set_mode(self, mode: str):
        allowed = ("passive", "active", "hybrid")
        if mode not in allowed:
            logger.warning("Attempted to set unknown mode: %s", mode)
            return
        logger.info("Setting mode: %s", mode)
        self.mode = mode

    def apply_behavior_profile(self, name: str):
        logger.info("Applying behavior profile: %s", name)
        if self.behavior_profiles and hasattr(self.behavior_profiles, "apply_profile"):
            try:
                cfg = self.behavior_profiles.apply_profile(name)
                if isinstance(cfg, dict):
                    self.mood = cfg.get("mood", self.mood)
                    self.snark_level = float(cfg.get("snark_level", self.snark_level))
                    self.energy = int(cfg.get("energy", self.energy))
                    self.focus = int(cfg.get("focus", self.focus))
                    logger.info("Behavior profile applied from module: %s", cfg)
                    return
            except Exception:
                logger.exception("behavior_profiles.apply_profile failed")

        presets = {
            "developer": {"mood": "neutral", "snark_level": 1.5, "energy": 85, "focus": 90},
            "grumpy": {"mood": "grumpy", "snark_level": 2.5, "energy": 60, "focus": 60},
            "assistant": {"mood": "cheerful", "snark_level": 0.5, "energy": 95, "focus": 80},
        }
        p = presets.get(name)
        if p:
            self.mood = p["mood"]
            self.snark_level = p["snark_level"]
            self.energy = p["energy"]
            self.focus = p["focus"]
            logger.info("Applied fallback behavior profile: %s", name)
        else:
            logger.warning("Unknown behavior profile and no external module: %s", name)
