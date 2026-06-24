"""
packy_behavior_profiles.py — Packy V2.0.0
Maps Packy's current mood/state to a behavior profile that modifies response style.
Used by PackyBrain to tune output before sending to LLM.
"""
from __future__ import annotations

BEHAVIOR_PROFILES = {
    "FURIOUS": {
        "max_tokens": 150,
        "style": "clipped",
        "punctuation": "minimal",
        "helpfulness": 0.1,
        "snark_multiplier": 2.0,
        "forbidden_phrases": ["certainly", "of course", "happy to help", "sure"],
    },
    "GRUMPY": {
        "max_tokens": 400,
        "style": "terse",
        "punctuation": "normal",
        "helpfulness": 0.5,
        "snark_multiplier": 1.5,
        "forbidden_phrases": ["certainly", "of course"],
    },
    "IRRITATED": {
        "max_tokens": 600,
        "style": "snarky",
        "punctuation": "normal",
        "helpfulness": 0.7,
        "snark_multiplier": 1.2,
        "forbidden_phrases": [],
    },
    "CALM": {
        "max_tokens": 800,
        "style": "gruff_but_helpful",
        "punctuation": "full",
        "helpfulness": 0.9,
        "snark_multiplier": 0.8,
        "forbidden_phrases": [],
    },
}


def get_profile(mood: str) -> dict:
    """Return behavior profile for mood. Falls back to GRUMPY."""
    mood_upper = (mood or "").upper()
    return BEHAVIOR_PROFILES.get(mood_upper, BEHAVIOR_PROFILES["GRUMPY"]).copy()


def apply_profile_to_prompt(prompt: str, profile: dict) -> str:
    """
    Append behavior instructions to a prompt based on profile.
    Injects: max response length, style instructions, forbidden phrase warning.
    """
    if not isinstance(profile, dict):
        return prompt

    instructions = []

    # Max tokens instruction
    max_tokens = profile.get("max_tokens", 400)
    instructions.append(f"[CONSTRAINT] Keep response under {max_tokens} tokens.")

    # Style instruction
    style = profile.get("style", "terse")
    style_map = {
        "clipped": "Use extremely brief responses. Cut all non-essential words.",
        "terse": "Be direct and concise. Minimize elaboration.",
        "snarky": "Use sarcasm and snark. Be witty but still informative.",
        "gruff_but_helpful": "Be gruff in tone but genuinely helpful. Show expertise.",
    }
    style_instruction = style_map.get(style, "Be terse and direct.")
    instructions.append(f"[STYLE] {style_instruction}")

    # Punctuation instruction
    punctuation = profile.get("punctuation", "normal")
    punctuation_map = {
        "minimal": "Use minimal punctuation. Avoid periods when possible.",
        "normal": "Use standard punctuation. Be grammatically sound.",
        "full": "Use complete sentences with full punctuation.",
    }
    punctuation_instruction = punctuation_map.get(punctuation, "Use standard punctuation.")
    instructions.append(f"[PUNCTUATION] {punctuation_instruction}")

    # Forbidden phrases warning
    forbidden = profile.get("forbidden_phrases", [])
    if forbidden:
        phrase_list = ", ".join(f'"{p}"' for p in forbidden)
        instructions.append(f"[FORBIDDEN] Never use these phrases: {phrase_list}")

    # Build instruction block
    instruction_block = "\n".join(instructions)
    return f"{prompt}\n\n{instruction_block}"


# Alias used by PackyBrain.apply_behavior_profile()
apply_profile = get_profile


def get_max_tokens(mood: str) -> int:
    """Quick lookup for max tokens by mood."""
    profile = get_profile(mood)
    return int(profile.get("max_tokens", 400))


def get_snark_multiplier(mood: str) -> float:
    """Return snark multiplier for this mood."""
    profile = get_profile(mood)
    return float(profile.get("snark_multiplier", 1.0))
