"""Feature gating — what each tier includes for Gargoyle Packy.

Tiers in increasing capability:

    community  - free / trial, single Discord server, direct mode
    indie      - small Discord, microservice mode
    pro        - multi-guild, custom persona, priority support
    enterprise - source + SLA + custom integrations

Features are explicit strings (never just "is_pro" booleans) so a new tier
can be added without changing the gating call sites.
"""

from __future__ import annotations

from typing import Final

# Tier names — kept as constants so call sites use the symbol, not the string.
TIER_COMMUNITY: Final = "community"
TIER_INDIE: Final = "indie"
TIER_PRO: Final = "pro"
TIER_ENTERPRISE: Final = "enterprise"

ALL_TIERS: Final = (TIER_COMMUNITY, TIER_INDIE, TIER_PRO, TIER_ENTERPRISE)

# Feature identifiers. Add new ones here and map them in TIER_FEATURES.
FEATURE_CORE_CHARACTER: Final = "core_character"
FEATURE_DISCORD_BOT: Final = "discord_bot"
FEATURE_MICROSERVICE_MODE: Final = "microservice_mode"
FEATURE_MULTI_GUILD: Final = "multi_guild"  # >1 Discord server
FEATURE_CUSTOM_PERSONA: Final = "custom_persona"
FEATURE_ADVANCED_LORE: Final = "advanced_lore"  # user-supplied lorebook
FEATURE_CHAOS_LAYER: Final = "chaos_layer"
FEATURE_PRIORITY_SUPPORT: Final = "priority_support"
FEATURE_SOURCE_CODE: Final = "source_code"
FEATURE_SLA: Final = "sla"

# Tier → set of included features.
# Keep this ordered from least to most capable.
TIER_FEATURES: Final[dict[str, frozenset[str]]] = {
    TIER_COMMUNITY: frozenset({
        FEATURE_CORE_CHARACTER,
        FEATURE_DISCORD_BOT,
    }),
    TIER_INDIE: frozenset({
        FEATURE_CORE_CHARACTER,
        FEATURE_DISCORD_BOT,
        FEATURE_MICROSERVICE_MODE,
        FEATURE_CHAOS_LAYER,
    }),
    TIER_PRO: frozenset({
        FEATURE_CORE_CHARACTER,
        FEATURE_DISCORD_BOT,
        FEATURE_MICROSERVICE_MODE,
        FEATURE_MULTI_GUILD,
        FEATURE_CUSTOM_PERSONA,
        FEATURE_ADVANCED_LORE,
        FEATURE_CHAOS_LAYER,
        FEATURE_PRIORITY_SUPPORT,
    }),
    TIER_ENTERPRISE: frozenset({
        FEATURE_CORE_CHARACTER,
        FEATURE_DISCORD_BOT,
        FEATURE_MICROSERVICE_MODE,
        FEATURE_MULTI_GUILD,
        FEATURE_CUSTOM_PERSONA,
        FEATURE_ADVANCED_LORE,
        FEATURE_CHAOS_LAYER,
        FEATURE_PRIORITY_SUPPORT,
        FEATURE_SOURCE_CODE,
        FEATURE_SLA,
    }),
}


def tier_includes(tier: str, feature: str) -> bool:
    """True if the named tier grants the named feature.

    Unknown tier or feature → False. Never raises. A misspelled feature name
    fails closed (no access), not open (full access).
    """
    features = TIER_FEATURES.get(tier.lower())
    if features is None:
        return False
    return feature in features


def required_tier_for(feature: str) -> str:
    """Lowest tier that grants a feature, for error messages.

    Returns "enterprise" if no public tier grants it.
    """
    for tier in (TIER_COMMUNITY, TIER_INDIE, TIER_PRO, TIER_ENTERPRISE):
        if feature in TIER_FEATURES[tier]:
            return tier
    return TIER_ENTERPRISE
