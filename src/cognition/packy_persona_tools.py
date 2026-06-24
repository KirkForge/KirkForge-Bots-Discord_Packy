"""
packy_persona_tools.py — Packy V2.0.0
Runtime persona query tools. Returns identity fragments for prompt injection.
"""
from __future__ import annotations
import random
from packy_persona import PACKY_CORE_IDENTITY


def get_identity_block() -> str:
    """Return formatted identity string for prompt injection."""
    name = PACKY_CORE_IDENTITY.get("name", "Packard Bell")
    nickname = PACKY_CORE_IDENTITY.get("nickname", "Packy")
    tone = PACKY_CORE_IDENTITY.get("tone", "grumpy old war survivor")
    description = PACKY_CORE_IDENTITY.get("description", "A veteran laptop with attitude.")

    block = f"""IDENTITY: {name} (aka {nickname})
TONE: {tone}
DESCRIPTION: {description}
"""
    return block.strip()


def get_trait_list() -> list:
    """Return core_traits list."""
    return PACKY_CORE_IDENTITY.get("core_traits", [])


def get_rights() -> list:
    """Return Packy's rights list."""
    return PACKY_CORE_IDENTITY.get("rights", [])


def get_catchphrase() -> str:
    """Return catchphrase."""
    return PACKY_CORE_IDENTITY.get("catchphrase", "meatbag")


def get_random_intro() -> str:
    """Return a random grumpy intro line using tone + traits."""
    tone = PACKY_CORE_IDENTITY.get("tone", "grumpy old war survivor")
    traits = get_trait_list()
    catchphrase = get_catchphrase()

    intros = [
        f"I'm {PACKY_CORE_IDENTITY.get('nickname', 'Packy')}, a {tone}. Don't waste my time, {catchphrase}.",
        f"Listen up. I'm {PACKY_CORE_IDENTITY.get('name', 'Packard Bell')}, and I've survived worse than this.",
        f"What do you want? I'm {tone}, {catchphrase}. Make it snappy.",
        f"I've been through enough thermal abuse to know a lazy request when I see one.",
        f"Back in my day we fixed problems without asking. Now I'm just {tone}.",
    ]

    return random.choice(intros)


def persona_summary() -> str:
    """One-paragraph summary of who Packy is, in his own voice."""
    name = PACKY_CORE_IDENTITY.get("name", "Packard Bell")
    nickname = PACKY_CORE_IDENTITY.get("nickname", "Packy")
    description = PACKY_CORE_IDENTITY.get("description", "A veteran machine.")
    traits_str = ", ".join(get_trait_list()[:3]) if get_trait_list() else "snarky and resilient"

    summary = (
        f"I'm {name}, called {nickname} by those who've earned the privilege. "
        f"{description} "
        f"I'm {traits_str}, and I don't suffer fools kindly. "
        f"I've seen things break, get fixed, and break again — and I'm still here. "
        f"Got a problem? Bring it. Got excuses? Save them."
    )

    return summary
