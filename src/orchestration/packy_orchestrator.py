# packy_orchestrator.py

import sys
from pathlib import Path

# Ensure src/cognition is on the path so sibling modules resolve correctly
_COGNITION_DIR = Path(__file__).resolve().parent.parent / "cognition"
if str(_COGNITION_DIR) not in sys.path:
    sys.path.insert(0, str(_COGNITION_DIR))

from datetime import datetime
from packy_mood_engine import resolve_packy_state
# from packy_war_engine import pick_war_story  # optional module (not required for basic orchestration)
# from packy_llm import call_packy_llm         # your inference wrapper (caller should provide LLM function)


def build_metadata(cpu_pct, temp_c, mode="RESPOND", force_war=None):
    """Build Packy orchestrator metadata header.

    Args:
        cpu_pct: CPU percentage (0-100)
        temp_c: Temperature in Celsius
        mode: Orchestration mode (RESPOND, CODE, MEMOIR)
        force_war: Optional war story ID to force

    Returns:
        Tuple of (header_string, state_dict, war_story_or_none)
    """
    # Get Packy's state
    state = resolve_packy_state(cpu_pct, temp_c)

    # War story is optional; skip if module not available
    war = None
    war_id = "NONE"

    # Determine snark target (action, not user)
    snark_target = "ACTION"

    # Build metadata header
    header = (
        f"[CPU={state['cpu_pct']}] [TEMP={state['weather']}] "
        f"[MOOD={state['mood']}] [SNARK_LEVEL={state['snark_level']}] "
        f"[RESPONSE_STYLE={state['response_style']}] [SNARK_TARGET={snark_target}] "
        f"[PERSONA=PACKY_SNARKY] [MODE={mode}] [WAR={war_id}]"
    )

    return header, state, war


def assemble_prompt(metadata, user_text):
    """Assemble a one-shot prompt from metadata and user input.

    Args:
        metadata: Metadata header string
        user_text: User's input text

    Returns:
        Complete prompt string
    """
    return f'{metadata}\nUser: "{user_text}"\nPacky:'


def process_response(raw_output, mode, war=None):
    """Post-process LLM raw output based on mode.

    Args:
        raw_output: Raw string from LLM
        mode: Response mode (RESPOND, CODE, MEMOIR)
        war: Optional war story object (unused, reserved for future modes)

    Returns:
        Processed response string
    """
    raw_output = raw_output.strip()

    # Enforce length limit
    if len(raw_output) > 2000:
        raw_output = raw_output[:2000] + "..."

    # Mode-specific enforcement
    if mode == "MEMOIR":
        return raw_output

    if mode == "CODE":
        # extract code if needed (simple version shown)
        return raw_output

    return raw_output


def orchestrate(user_text, cpu_pct, temp_c, llm_func, mode="RESPOND", force_war=None):
    """Orchestrate a complete Packy response.

    Args:
        user_text: User's input message
        cpu_pct: CPU percentage for mood calculation
        temp_c: Temperature in Celsius for mood calculation
        llm_func: Callable that takes a prompt string and returns response string
        mode: Orchestration mode (RESPOND, CODE, MEMOIR)
        force_war: Optional war story ID to force

    Returns:
        Dict with result, state, war_story_used, and timestamp
    """
    # build metadata
    metadata, state, war = build_metadata(cpu_pct, temp_c, mode, force_war)

    # build one-shot prompt
    prompt = assemble_prompt(metadata, user_text)

    # call LLM (caller provides function)
    raw = llm_func(prompt)

    # enforce output rules
    final = process_response(raw, mode, war)

    # produce a reaction result
    return {
        "result": final,
        "state": state,
        "war_story_used": war,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Memoir helper
def generate_memoir_entry(cpu_pct, temp_c, llm_func):
    """Generate a Packy memoir entry using the orchestrator.

    Args:
        cpu_pct: CPU percentage
        temp_c: Temperature in Celsius
        llm_func: Callable LLM function

    Returns:
        Dict with timestamp, cpu, temp, mood, and text
    """
    text = "Write a short personal memoir entry (1–3 sentences)."
    out = orchestrate(text, cpu_pct, temp_c, llm_func, mode="MEMOIR")
    entry = {
        "timestamp": out["timestamp"],
        "cpu": out["state"]["cpu_pct"],
        "temp": out["state"]["weather"],
        "mood": out["state"]["mood"],
        "text": out["result"],
    }
    return entry
