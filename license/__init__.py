"""License layer for Gargoyle Packy (KirkForge).

Public API — the rest of the product imports from here only:

    from license import load, LoadedLicense, require_feature, LicenseError

Boot flow:

    1. `packy_endpoint.py` calls `load()` at startup.
    2. On any LicenseError, the product prints a clear message and exits 1.
    3. Optional features (microservice mode, custom persona) call
       `require_feature(...)` lazily — they're gated without crashing boot.

The signature is verified before any claim value is trusted, so a forged
license with `tier = "enterprise"` is still rejected.
"""

from __future__ import annotations

import logging

from .claims import LICENSE_FORMAT_VERSION, Customer, LicenseClaims
from .errors import (
    LicenseError,
    LicenseExpiredError,
    LicenseFeatureUnavailable,
    LicenseFormatError,
    LicenseNotFoundError,
    LicenseProductMismatchError,
    LicenseSignatureError,
    LicenseTamperError,
)
from .features import (
    ALL_TIERS,
    FEATURE_ADVANCED_LORE,
    FEATURE_CHAOS_LAYER,
    FEATURE_CORE_CHARACTER,
    FEATURE_CUSTOM_PERSONA,
    FEATURE_DISCORD_BOT,
    FEATURE_MICROSERVICE_MODE,
    FEATURE_MULTI_GUILD,
    FEATURE_PRIORITY_SUPPORT,
    FEATURE_SLA,
    FEATURE_SOURCE_CODE,
    TIER_COMMUNITY,
    TIER_ENTERPRISE,
    TIER_INDIE,
    TIER_PRO,
    TIER_FEATURES,
    required_tier_for,
    tier_includes,
)
from .loader import PRODUCT_ID, LoadedLicense, load
from .paths import ENV_LICENSE_PATH, find_license_file, search_paths

logger = logging.getLogger(__name__)

__all__ = [
    # Loaders
    "load",
    "LoadedLicense",
    "PRODUCT_ID",
    "find_license_file",
    "search_paths",
    "ENV_LICENSE_PATH",
    # Claims
    "LicenseClaims",
    "Customer",
    "LICENSE_FORMAT_VERSION",
    # Tiers + features
    "TIER_COMMUNITY",
    "TIER_INDIE",
    "TIER_PRO",
    "TIER_ENTERPRISE",
    "ALL_TIERS",
    "TIER_FEATURES",
    "FEATURE_CORE_CHARACTER",
    "FEATURE_DISCORD_BOT",
    "FEATURE_MICROSERVICE_MODE",
    "FEATURE_MULTI_GUILD",
    "FEATURE_CUSTOM_PERSONA",
    "FEATURE_ADVANCED_LORE",
    "FEATURE_CHAOS_LAYER",
    "FEATURE_PRIORITY_SUPPORT",
    "FEATURE_SOURCE_CODE",
    "FEATURE_SLA",
    "tier_includes",
    "required_tier_for",
    # Errors
    "LicenseError",
    "LicenseNotFoundError",
    "LicenseFormatError",
    "LicenseSignatureError",
    "LicenseExpiredError",
    "LicenseFeatureUnavailable",
    "LicenseProductMismatchError",
    "LicenseTamperError",
    # Globals
    "current",
]

# Process-wide license handle. Set once at boot, read everywhere.
# Lazy default to None so importing this module doesn't try to load.
current: LoadedLicense | None = None


def require_feature(feature: str) -> None:
    """Raise LicenseFeatureUnavailable if the current license lacks `feature`.

    Call sites:

        from license import require_feature, FEATURE_DISCORD_BOT
        def start_discord_bot():
            require_feature(FEATURE_DISCORD_BOT)
            ...

    Fail-closed: an uninitialized license (current is None) is treated as
    no features granted. This is the safe default for a service that
    somehow runs without having called `load()` yet.
    """
    if current is None:
        raise LicenseFeatureUnavailable(
            "license not loaded — call `license.load()` at boot before using features"
        )
    if not current.has_feature(feature):
        from .features import required_tier_for  # local: keep public surface clean

        raise LicenseFeatureUnavailable(
            f"Feature '{feature}' requires the '{required_tier_for(feature)}' tier. "
            f"Your license is '{current.tier}'. Upgrade at "
            f"https://kirkforge.com/packy/pricing"
        )
