"""License claims — the data carried in a signed license file.

Keep this dataclass narrow. The signed payload is `to_dict()` minus the
`signature` field; everything else is asserted by signature.

This file is product-agnostic; the loader pins the product string
when it asserts the claims.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


# Bump when the on-disk format changes in a way older loaders can't read.
LICENSE_FORMAT_VERSION = 1


@dataclass(frozen=True)
class Customer:
    name: str
    email: str


@dataclass(frozen=True)
class LicenseClaims:
    """The verifiable claims inside a license file.

    Frozen so once parsed and verified, the loader's callers can't mutate
    the trusted data accidentally.
    """

    license_id: str
    product: str
    product_version: str
    format_version: int
    customer: Customer
    tier: str
    issued_at: datetime
    support_until: datetime
    max_seats: int
    features: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["issued_at"] = self.issued_at.astimezone(timezone.utc).isoformat()
        d["support_until"] = self.support_until.astimezone(timezone.utc).isoformat()
        d["features"] = list(self.features)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LicenseClaims":
        try:
            cust = d["customer"]
            return cls(
                license_id=str(d["license_id"]),
                product=str(d["product"]),
                product_version=str(d["product_version"]),
                format_version=int(d.get("format_version", LICENSE_FORMAT_VERSION)),
                customer=Customer(name=str(cust["name"]), email=str(cust["email"])),
                tier=str(d["tier"]).lower(),
                issued_at=_parse_iso(d["issued_at"]),
                support_until=_parse_iso(d["support_until"]),
                max_seats=int(d["max_seats"]),
                features=tuple(str(f) for f in d.get("features", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"malformed license claims: {exc}") from exc

    def is_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        # Support contract expiry doesn't kill the product — it just gates
        # support-dependent features. License itself is perpetual.
        return now > self.support_until


def _parse_iso(s: str) -> datetime:
    # Python's fromisoformat in 3.11+ handles "Z" suffix.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)
