# packy_mood_engine.py
# Core CPU + Weather mood matrix for Packy

from typing import Tuple


def cpu_mood(cpu_pct: int) -> Tuple[str, str, str]:
    """Return base mood and snark level from pure CPU load.

    Args:
        cpu_pct: CPU percentage (0-100)

    Returns:
        Tuple of (mood, snark_level, response_style)
    """
    if not isinstance(cpu_pct, (int, float)):
        cpu_pct = 0

    if cpu_pct >= 80:
        return "FURIOUS", "MAX", "CLIPPED"
    elif cpu_pct >= 60:
        return "GRUMPY", "HIGH", "TERSE"
    elif cpu_pct >= 30:
        return "IRRITATED", "MEDIUM", "SNARKY"
    else:
        return "CALM", "LOW", "SHORT"


def weather_modifier(temp_c: float) -> str:
    """Determine weather emotional modifier.

    Args:
        temp_c: Temperature in Celsius

    Returns:
        Modifier string: OVERHEATED, COMFORTED, or NEUTRAL
    """
    if not isinstance(temp_c, (int, float)):
        temp_c = 20

    if temp_c > 25:
        return "OVERHEATED"
    elif temp_c < 10:
        return "COMFORTED"
    return "NEUTRAL"


def combine_mood(base_mood: str, modifier: str) -> str:
    """Combine CPU mood + weather modifier.

    Args:
        base_mood: Base mood string
        modifier: Weather modifier string

    Returns:
        Combined mood string
    """
    if modifier == "NEUTRAL":
        return base_mood
    return f"{base_mood}-{modifier}"


def resolve_packy_state(cpu_pct: int, temp_c: float) -> dict:
    """Resolve Packy's emotional state from system metrics.

    Args:
        cpu_pct: CPU percentage (0-100)
        temp_c: Temperature in Celsius

    Returns:
        Dict with keys:
            mood: final mood string (e.g., 'GRUMPY-OVERHEATED')
            snark_level: LOW / MEDIUM / HIGH / MAX
            response_style: SHORT / SNARKY / TERSE / CLIPPED
            cpu_pct: Input CPU percentage
            weather: Weather modifier
    """
    base_mood, snark, style = cpu_mood(cpu_pct)
    modifier = weather_modifier(temp_c)
    final_mood = combine_mood(base_mood, modifier)

    return {
        "mood": final_mood,
        "snark_level": snark,
        "response_style": style,
        "cpu_pct": cpu_pct,
        "weather": modifier,
    }


# Example usage:
if __name__ == "__main__":
    print(resolve_packy_state(cpu_pct=85, temp_c=28))
    # {'mood': 'FURIOUS-OVERHEATED', 'snark_level': 'MAX', 'response_style': 'CLIPPED', ...}
