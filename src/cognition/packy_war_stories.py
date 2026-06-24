"""
packy_war_stories.py — Gargoyle Packy V2.0.0
War story loader and picker. Used by orchestrator for prompt enrichment.
"""
import json
import random
from pathlib import Path

WAR_STORIES_PATH = Path(__file__).parent.parent.parent / "data" / "packy_war_stories.json"
_stories: list = []


def load_war_stories() -> list:
    """
    Load war stories from JSON. Caches result.

    Returns:
        List of war story dicts, or empty list on error.
    """
    global _stories
    if _stories:
        return _stories

    try:
        with open(WAR_STORIES_PATH, "r", encoding="utf-8") as f:
            _stories = json.load(f)
            return _stories
    except Exception:
        return []


def pick_war_story(force_id: int = None, mood: str = None, chance: float = 0.25) -> dict | None:
    """
    Return a war story or None.

    Args:
        force_id: Return specific story by id. If provided, ignores mood and chance.
        mood: Prefer stories matching mood_required (or "ANY"). If no match found,
              returns None unless chance still triggers a random pick.
        chance: Probability of returning a story at all (default 25%). Only used
               if force_id is None.

    Returns:
        A war story dict, or None.
    """
    stories = load_war_stories()
    if not stories:
        return None

    # Force a specific story by ID
    if force_id is not None:
        story = next((s for s in stories if s.get("id") == force_id), None)
        return story

    # Filter by mood if specified
    if mood is not None:
        mood_stories = [
            s for s in stories
            if s.get("mood_required") == mood or s.get("mood_required") == "ANY"
        ]
        if mood_stories and random.random() < chance:
            return random.choice(mood_stories)
        return None

    # Default: probabilistic injection without mood filtering
    if random.random() < chance:
        return random.choice(stories)

    return None


def get_all_stories() -> list:
    """
    Return all war stories.

    Returns:
        List of all war story dicts.
    """
    return load_war_stories()


def format_war_story_for_prompt(story: dict) -> str:
    """
    Return formatted string for inclusion in LLM prompts.

    Format: '[WAR: {title}] {lead} {full}'

    Args:
        story: A war story dict with 'title', 'lead', and 'full' keys.

    Returns:
        Formatted string ready for prompt injection.
    """
    if not story:
        return ""

    title = story.get("title", "Unknown")
    lead = story.get("lead", "")
    full = story.get("full", "")

    return f"[WAR: {title}] {lead} {full}"
