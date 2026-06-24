# modules/packy_war_header.py
from datetime import datetime
import random

# Prefer using Packy's snark & lore if available
try:
    from packy_snark import _get_pool as _snark_pool
except Exception:
    _snark_pool = None

# Small curated war-story templates (rotate + fill)
WAR_STORY_TEMPLATES = [
    ("Thermal Martyrdom", "I once survived 105°C. This header is cooler than that."),
    ("Terrace Exile", "Terrace Exile 2025 taught me to survive on duct tape and doom."),
    ("Pizza Incident", "Warning: pizza trauma present. Consume code at your own risk."),
    ("BIOS Flashback", "BIOS flashing memories included — ear plugs recommended."),
]

def _get_snark_excerpt(n=2):
    pool = None
    if _snark_pool:
        try:
            pool = _snark_pool()
        except Exception:
            pool = None
    if not pool:
        # fallback minimal snark
        return ["Packy: back when floppies mattered...", "If this breaks, blame the meatbag."]
    return random.sample(pool, min(n, len(pool)))

def build_war_header(task_description=None, include_time=True, lines=3):
    """
    Returns a multi-line war-story header string suitable for inserting at top of generated scripts.
    """
    title, lead = random.choice(WAR_STORY_TEMPLATES)
    timestamp = datetime.utcnow().isoformat() + "Z" if include_time else ""
    snark_lines = _get_snark_excerpt(lines)

    hdr_lines = ["# -------------------------------------------------------------"]
    hdr_lines.append(f"# Packy War-Story: {title}")
    if timestamp:
        hdr_lines.append(f"# Generated: {timestamp}")
    if task_description:
        hdr_lines.append(f"# Task: {task_description}")
    hdr_lines.append(f"# {lead}")
    hdr_lines.append("#")
    for l in snark_lines:
        # normalize to single-line comment prefix
        comment = l.replace("\n", " ").strip()
        hdr_lines.append(f"# {comment}")
    hdr_lines.append("# -------------------------------------------------------------")
    return "\n".join(hdr_lines) + "\n\n"
