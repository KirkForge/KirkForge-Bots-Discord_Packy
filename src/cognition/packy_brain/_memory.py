"""PackyMemoryMixin — remember / recent / write_lore backends.

Extracted from packy_brain.py lines 587-632.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ._setup import logger

logger = logging.getLogger("packy.brain.memory")


class PackyMemoryMixin:
    def remember(self, text: str, tags: Optional[List[str]] = None) -> bool:
        if self.memory is None and self.memory_adapter is None:
            logger.warning("No memory backend available; remember() skipped")
            return False
        tags = tags or []
        try:
            if self.memory_adapter and hasattr(self.memory_adapter, "add"):
                return bool(self.memory_adapter.add(text, tags=tags))
            if hasattr(self.memory, "add_memory"):
                self.memory.add_memory(text, tags=tags)
                return True
            if isinstance(self.memory, dict):
                self.memory.setdefault("memories", []).append({"text": text, "tags": tags})
                return True
        except Exception:
            logger.exception("remember() failed")
            return False
        logger.warning("Memory backend has no recognized interface; remember() skipped")
        return False

    def recent_memories(self, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            if self.memory_adapter and hasattr(self.memory_adapter, "recent"):
                return list(self.memory_adapter.recent(limit=limit))
            if hasattr(self.memory, "recent"):
                return list(self.memory.recent(limit=limit))
            if isinstance(self.memory, dict):
                return list(self.memory.get("memories", [])[-limit:])
        except Exception:
            logger.exception("recent_memories failed")
        return []

    def write_lore(self, text: str, tags: Optional[List[str]] = None) -> bool:
        tags = tags or []
        try:
            if self.lore_writer and hasattr(self.lore_writer, "write_lore"):
                return bool(self.lore_writer.write_lore(text, tags or []))
        except Exception:
            logger.exception("lore_writer.write_lore failed")
        return self.remember(text, tags)
