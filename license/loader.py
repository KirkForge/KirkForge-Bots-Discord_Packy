"""License loader — find file, parse JSON, verify signature, return claims.

The single entry point the rest of the product uses. After loading, the
returned `LoadedLicense` is safe to query for tier/features/expiration.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .claims import LicenseClaims
from .errors import (
    LicenseError,
    LicenseFormatError,
    LicenseNotFoundError,
    LicenseProductMismatchError,
    LicenseSignatureError,
)
from .paths import ENV_LICENSE_PATH, find_license_file
from .verifier import verify_signature

logger = logging.getLogger(__name__)


# Pinned product name for this build. A Packy license doesn't unlock other
# products and vice versa. If we ever ship a multi-product suite, lift this
# to a config setting.
PRODUCT_ID = "gargoyle-packy"


@dataclass(frozen=True)
class LoadedLicense:
    """The verified license plus its source path.

    The `claims` field is immutable; query it instead of re-parsing.
    """

    claims: LicenseClaims
    source_path: Path

    @property
    def tier(self) -> str:
        return self.claims.tier

    @property
    def customer_name(self) -> str:
        return self.claims.customer.name

    @property
    def license_id(self) -> str:
        return self.claims.license_id

    def has_feature(self, feature: str) -> bool:
        from .features import tier_includes  # avoid circular at module load

        return tier_includes(self.claims.tier, feature)

    def support_expired(self, now: datetime | None = None) -> bool:
        return self.claims.is_expired(now)

    def summary(self) -> dict[str, object]:
        """Human-readable summary for the admin endpoint / status line."""
        return {
            "license_id": self.claims.license_id,
            "tier": self.claims.tier,
            "customer": self.claims.customer.name,
            "email": self.claims.customer.email,
            "max_seats": self.claims.max_seats,
            "issued_at": self.claims.issued_at.isoformat(),
            "support_until": self.claims.support_until.isoformat(),
            "support_active": not self.support_expired(),
            "source_path": str(self.source_path),
        }


def load(path: Path | str | None = None) -> LoadedLicense:
    """Find, parse, and verify a license file. Returns a LoadedLicense.

    `path` arg is an override; when omitted, the standard search paths are
    used. Raises one of the LicenseError subclasses on any problem.
    """
    if path is not None:
        license_path = Path(path)
        if not license_path.is_file():
            raise LicenseNotFoundError(
                f"Explicit license path does not exist: {license_path}\n"
                f"Set the {ENV_LICENSE_PATH} environment variable to a real "
                f"file, or remove the override to use the default search paths."
            )
    else:
        license_path = find_license_file()
    logger.debug("loading license from %s", license_path)

    try:
        raw = license_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise LicenseFormatError(f"could not read license at {license_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise LicenseFormatError("license file must contain a JSON object at the top level")

    # 1. Verify signature BEFORE we look at any claim value. A forged license
    #    that happens to have a valid `tier` field is still rejected.
    try:
        verify_signature(data)
    except (LicenseFormatError, LicenseSignatureError):
        raise

    # 2. Parse claims now that we trust the payload.
    try:
        claims = LicenseClaims.from_dict(data)
    except ValueError as exc:
        raise LicenseFormatError(str(exc)) from exc

    # 3. Product must match. A Packy license doesn't unlock other products.
    if claims.product != PRODUCT_ID:
        raise LicenseProductMismatchError(
            f"this license is for '{claims.product}', not '{PRODUCT_ID}'"
        )

    # 4. Format version guard. If we bump the format, the loader must decide
    #    here whether it can read the new shape.
    from .claims import LICENSE_FORMAT_VERSION  # local import: avoid cycle

    if claims.format_version > LICENSE_FORMAT_VERSION:
        raise LicenseFormatError(
            f"license format version {claims.format_version} is newer than this "
            f"product supports (max {LICENSE_FORMAT_VERSION}). Please update Gargoyle Packy."
        )

    return LoadedLicense(claims=claims, source_path=license_path)
