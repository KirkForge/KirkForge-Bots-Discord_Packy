"""PackySummaryMixin — CLI/API summary() helper.

Extracted from packy_brain.py lines 770-793.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ._setup import logger

logger = logging.getLogger("packy.brain.summary")


class PackySummaryMixin:
    def summary(self) -> Dict[str, Any]:
        try:
            persona_repr = getattr(self.persona, "__dict__", self.persona)
            return {
                "version": self.VERSION,
                "mood": self.mood,
                "mode": self.mode,
                "snark_level": self.snark_level,
                "energy": self.energy,
                "focus": self.focus,
                "persona": persona_repr,
                "structured_lore_loaded": self.lore_loaded_from_structured,
                "category_counts": self.category_counts,
                "memory_available": self.memory is not None,
                "cognition_available": self.cog is not None,
            }
        except Exception:
            logger.exception("summary() failed; returning minimal status")
            return {
                "version": self.VERSION,
                "mood": self.mood,
                "mode": self.mode,
                "snark_level": self.snark_level,
            }
