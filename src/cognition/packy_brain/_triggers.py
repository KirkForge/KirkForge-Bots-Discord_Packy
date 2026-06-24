"""PackyTriggersMixin — keyword trigger detection + profanity scoring.

Extracted from packy_brain.py lines 384-423.
"""

from __future__ import annotations

import logging
from typing import List, Tuple

from ._setup import logger

logger = logging.getLogger("packy.brain.triggers")


class PackyTriggersMixin:
    def detect_triggers(self, text: str) -> Tuple[List[str], float]:
        low = (text or "").lower()
        matches: dict = {}

        for cat, kws in (self.trigger_map or {}).items():
            if not kws:
                continue
            for kw in kws:
                try:
                    if kw and kw.lower() in low:
                        matches[cat] = matches.get(cat, 0) + 1
                except Exception:
                    continue

        if not matches and "categories" in self.structured_lore:
            for cat in self.structured_lore.get("categories", {}).keys():
                try:
                    for kw in (cat.split("_") if "_" in cat else [cat]):
                        if kw and kw.lower() in low:
                            matches[cat] = matches.get(cat, 0) + 1
                except Exception:
                    continue

        ordered = sorted(matches.items(), key=lambda x: x[1], reverse=True)
        matched_categories = [k for k, v in ordered]

        profanity_score = 0.0
        for pat, weight in self.profanity_map.items():
            try:
                if pat.search(text or ""):
                    profanity_score += weight
            except Exception:
                continue

        return matched_categories, profanity_score
