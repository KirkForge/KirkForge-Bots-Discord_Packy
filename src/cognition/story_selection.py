import random, json
from pathlib import Path

_STORIES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "packy_war_stories.json"

def pick_war_story(force_id=None, severity=None):
    with open(_STORIES_PATH, encoding="utf-8") as f:
        all_stories = json.load(f)

    if force_id:
        return next((s for s in all_stories if s["id"] == force_id), None)

    if severity:
        # Data uses mood_required; fall back to tag match for legacy severity values
        candidates = [s for s in all_stories if s.get("mood_required") == severity or severity in s.get("tags", [])]
        if not candidates:
            candidates = all_stories
    else:
        candidates = all_stories

    return random.choice(candidates) if candidates else None
