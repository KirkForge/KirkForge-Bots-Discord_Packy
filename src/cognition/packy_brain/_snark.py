"""PackySnarkMixin — selecting snark lines from structured lore.

Extracted from packy_brain.py lines 425-493.
"""

from __future__ import annotations

import logging
import random
from typing import List, Optional

from ._setup import _default_get_snark_lines, logger

logger = logging.getLogger("packy.brain.snark")


class PackySnarkMixin:
    def _get_lines_for_category(self, category: str) -> List[str]:
        if not self.lore_loaded_from_structured:
            return []
        try:
            return list(self.structured_lore.get("categories", {}).get(category, [])[:])
        except Exception:
            logger.exception("Error getting lines for category %s", category)
            return []

    def get_snark_lines(self, n: int = 3, categories: Optional[List[str]] = None) -> List[str]:
        out: List[str] = []
        try:
            if categories:
                for cat in categories:
                    lines = self._get_lines_for_category(cat)
                    if lines:
                        out.extend(random.sample(lines, min(len(lines), n - len(out))))
                    if len(out) >= n:
                        return out[:n]

            if self.lore_loaded_from_structured and "categories" in self.structured_lore:
                cats = sorted(self.structured_lore["categories"].items(), key=lambda x: len(x[1]) if x[1] else 0, reverse=True)
                for cat, lines in cats:
                    if not lines:
                        continue
                    take = min(len(lines), n - len(out))
                    out.extend(random.sample(lines, take))
                    if len(out) >= n:
                        return out[:n]

            if self.snark_engine and hasattr(self.snark_engine, "get_snark_lines"):
                try:
                    module_lines = list(self.snark_engine.get_snark_lines(n))
                    if module_lines:
                        out.extend(module_lines)
                except Exception:
                    logger.exception("snark_engine.get_snark_lines failed")

            if self.snark and hasattr(self.snark, "get_snark_lines"):
                try:
                    module_lines = list(self.snark.get_snark_lines(n))
                    if module_lines:
                        out.extend(module_lines)
                except Exception:
                    logger.exception("snark.get_snark_lines failed")

            if len(out) < n:
                candidates = []
                candidates.extend(self.unfinished_snark or [])
                candidates.extend(self.static_lore_raw or [])
                if candidates:
                    needed = n - len(out)
                    picks = random.sample(candidates, min(len(candidates), needed))
                    out.extend(picks)

            if len(out) < n:
                out.extend(_default_get_snark_lines(n - len(out)))
        except Exception:
            logger.exception("get_snark_lines failed; returning default lines")
            out = _default_get_snark_lines(n)

        return out[:n]
