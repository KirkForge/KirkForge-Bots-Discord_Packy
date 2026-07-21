"""PackyTeachMixin — teach() and explain() interfaces.

Extracted from packy_brain.py lines 661-690.
"""

from __future__ import annotations

import logging
import random
from typing import List

logger = logging.getLogger("packy.brain.teach")


class PackyTeachMixin:
    def teach(self, topic: str) -> str:
        try:
            if self.teaching and hasattr(self.teaching, "teach"):
                return self.teaching.teach(topic)
        except Exception:
            logger.exception("teaching.teach failed")

        snippets: List[str] = []
        if self.lore_loaded_from_structured:
            for cat, lines in self.structured_lore.get("categories", {}).items():
                if topic.lower() in cat:
                    snippets.extend(lines)
            if not snippets:
                snippets = self.structured_lore.get("categories", {}).get("programming_snark", [])[
                    :5
                ]
        else:
            snippets = self.static_lore_raw[:5]

        if snippets:
            sample = random.choice(snippets)
            return f"Teaching stub on {topic}: {sample}"
        return f"Teaching stub on {topic}: I know nothing about {topic} yet."

    def explain(self, topic: str, style: str = "normal") -> str:
        if style == "snark":
            base = self.teach(topic)
            return self.inject_snark(base, {"source": "teach", "topic": topic})
        return self.teach(topic)
