"""
memory_adapter.py — Optional thin adapter for persistent memory

Purpose:
- Give PackyBrain a stable interface even if packy_memory.py changes internally.
- Avoid rewriting PackyBrain every time memory format evolves.

This adapter is NOT required but recommended for Packy 2.05.
"""

from __future__ import annotations
import logging

logger = logging.getLogger("packy.memory_adapter")


class MemoryAdapter:
    def __init__(self, backend):
        """
        backend can be:
        - persistent.packy_memory.PackyMemory instance
        - dict from persistant_loader.load_all()
        """
        self.backend = backend

    def add(self, text: str, tags=None):
        tags = tags or []
        try:
            if hasattr(self.backend, "add_memory"):
                return self.backend.add_memory(text, tags=tags)
            if isinstance(self.backend, dict):
                self.backend.setdefault("memories", []).append({"text": text, "tags": tags})
                return True
        except Exception:
            logger.exception("Failed to add memory")
        return False

    def recent(self, limit=20):
        try:
            if hasattr(self.backend, "recent"):
                return self.backend.recent(limit=limit)
            if isinstance(self.backend, dict):
                return self.backend.get("memories", [])[-limit:]
        except Exception:
            logger.exception("Failed to retrieve recent memories")
        return []
