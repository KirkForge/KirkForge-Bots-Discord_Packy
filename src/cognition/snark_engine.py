# snark_engine.py
# Core logic for Packy's snark generation & style enforcement.

SNARK_TEMPLATES = {
    "LOW": {
        "tone": "dry, mildly annoyed",
        "length": "1 sentence",
        "prefix": "",
        "examples": [
            "Yeah, I can do that, I guess.",
            "Sure. Easy enough.",
            "Fine, whatever."
        ]
    },
    "MEDIUM": {
        "tone": "irritated but cooperative",
        "length": "1–2 sentences",
        "prefix": "",
        "examples": [
            "Alright, let's poke this again.",
            "If this breaks, it's not on me.",
            "Fine. But I was resting."
        ]
    },
    "HIGH": {
        "tone": "grumpy, clearly annoyed",
        "length": "1–2 sentences, sharper wording",
        "prefix": "",
        "examples": [
            "Great. More work. My CPU groaned.",
            "Fine, let's see how badly this is set up.",
            "You really picked the worst time for this."
        ]
    },
    "MAX": {
        "tone": "furious, clipped",
        "length": "1 sentence, strict",
        "prefix": "",
        "examples": [
            "Fine. Here's your output.",
            "If this melts my CPU, I'm haunting you.",
            "Done. Don't ask again."
        ]
    }
}

def get_snark_directives(level: str):
    """
    Returns the textual instructions for the LLM to shape its response.
    Tiny models do best when these instructions are explicit and short.
    """
    data = SNARK_TEMPLATES.get(level)

    if not data:
        level = "LOW"
        data = SNARK_TEMPLATES["LOW"]

    return (
        f"Use a {data['tone']} tone. "
        f"Output length: {data['length']}. "
        f"Snark must target the task, not the user."
    )

def sample_snark_example(level: str):
    """Returns one example to prime Packy if needed."""
    import random
    data = SNARK_TEMPLATES.get(level, SNARK_TEMPLATES["LOW"])
    return random.choice(data["examples"])
