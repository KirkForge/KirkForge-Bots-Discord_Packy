"""License signing — wraps the operator-only keygen logic.

In production this is the only place the private signing key is loaded.
The key is on disk in PEM form (mode 600) and loaded once at startup.
"""

from __future__ import annotations

import base64
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from license.claims import LICENSE_FORMAT_VERSION, Customer, LicenseClaims
from license.features import TIER_FEATURES
from sales.config import tier_to_seats, tier_to_support_years

logger = logging.getLogger(__name__)


@dataclass
class SignRequest:
    tier: str                       # "indie" | "pro" | "enterprise"
    customer_name: str
    customer_email: str
    product_id: str                 # "the-specialist"
    product_version: str            # "1.0.0"


@dataclass
class SignResult:
    license_id: str
    license_json: str               # signed, ready to write to disk
    signed_at: datetime
    support_until: datetime
    seats: int
    features: list[str]


class LicenseSigner:
    """Loads the private key once, signs many claims objects."""

    def __init__(self, private_key_path: Path):
        if not private_key_path.is_file():
            raise SystemExit(
                f"FATAL: license private key not found at {private_key_path}"
            )
        try:
            mode = private_key_path.stat().st_mode & 0o777
            if mode & 0o077:
                logger.warning(
                    "License private key %s has permissive mode %04o — "
                    "should be 0600. Run: chmod 600 %s",
                    private_key_path, mode, private_key_path,
                )
        except OSError:
            pass
        with open(private_key_path, "rb") as fh:
            key_data = fh.read()
        key = load_pem_private_key(key_data, password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise SystemExit(
                f"FATAL: {private_key_path} is not an Ed25519 private key"
            )
        self._key = key

    def sign(self, req: SignRequest) -> SignResult:
        license_id = _new_license_id()
        now = datetime.now(timezone.utc)
        support_until = now + timedelta(days=365 * tier_to_support_years(req.tier))
        features = sorted(TIER_FEATURES[req.tier])

        claims = LicenseClaims(
            license_id=license_id,
            product=req.product_id,
            product_version=req.product_version,
            format_version=LICENSE_FORMAT_VERSION,
            customer=Customer(name=req.customer_name, email=req.customer_email),
            tier=req.tier,
            issued_at=now,
            support_until=support_until,
            max_seats=tier_to_seats(req.tier),
            features=tuple(features),
        )
        # Mirror the test conftest signing format: canonical JSON, no whitespace,
        # sorted keys, then Ed25519 over the bytes.
        payload = json.dumps(
            claims.to_dict(), separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        sig = self._key.sign(payload)
        out = claims.to_dict()
        out["signature"] = base64.b64encode(sig).decode("ascii")
        license_json = json.dumps(out, indent=2, sort_keys=True)

        return SignResult(
            license_id=license_id,
            license_json=license_json,
            signed_at=now,
            support_until=support_until,
            seats=tier_to_seats(req.tier),
            features=features,
        )


def _new_license_id() -> str:
    """KFG-PROD-XXXXXXXX — 8 random hex chars, easy to read aloud
    when the customer is checking their portal."""
    return f"KFG-PROD-{secrets.token_hex(4).upper()}"
