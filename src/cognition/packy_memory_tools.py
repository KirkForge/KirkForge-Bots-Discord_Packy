"""
packy_memory_tools.py — Packy V2.0.0
Memory query and write tools. Called by PackyBrain when remembering or storing things.
"""
from __future__ import annotations
import json
import os
import uuid
import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).parent.parent.parent / "data" / "packy_memory.json"


def load_memories() -> list:
    """Load all stored memories. Returns empty list on failure."""
    try:
        if not MEMORY_FILE.exists():
            return []

        content = MEMORY_FILE.read_text(encoding="utf-8")
        if not content.strip():
            return []

        data = json.loads(content)
        if isinstance(data, dict) and "memories" in data:
            return data["memories"]
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_memory(text: str, tags: list = None, mood: str = "GRUMPY") -> dict:
    """Create and save a new memory entry. Returns the entry."""
    tags = tags or []
    memory_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.now().isoformat()

    entry = {
        "id": memory_id,
        "text": text,
        "tags": tags,
        "mood": mood,
        "timestamp": timestamp,
    }

    try:
        # Ensure data directory exists
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Load existing memories
        memories = load_memories()

        # Append new memory
        memories.append(entry)

        # Save back to file
        MEMORY_FILE.write_text(
            json.dumps({"memories": memories}, indent=2),
            encoding="utf-8"
        )
        return entry
    except Exception:
        return entry


def recall_memories(query: str = None, n: int = 5) -> list:
    """Return n memories, optionally filtered by query keyword match."""
    memories = load_memories()

    if not query:
        # Return last n memories (most recent first)
        return list(reversed(memories[-n:]))

    # Filter by query keyword match
    query_lower = query.lower()
    filtered = [
        m for m in memories
        if query_lower in m.get("text", "").lower() or
           any(query_lower in tag.lower() for tag in m.get("tags", []))
    ]

    # Return last n matching memories (most recent first)
    return list(reversed(filtered[-n:]))


def forget_memory(memory_id: str) -> bool:
    """Remove a memory by id. Returns True if removed."""
    try:
        memories = load_memories()
        original_count = len(memories)

        # Filter out the memory with the matching id
        memories = [m for m in memories if m.get("id") != memory_id]

        if len(memories) < original_count:
            # Memory was removed, save the updated list
            MEMORY_FILE.write_text(
                json.dumps({"memories": memories}, indent=2),
                encoding="utf-8"
            )
            return True
        return False
    except Exception:
        return False


def memory_count() -> int:
    """Return total number of stored memories."""
    return len(load_memories())
