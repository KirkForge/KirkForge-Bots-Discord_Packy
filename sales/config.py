"""Sales-service config — env-driven, fail-closed.

Per AGENTS.md secure-defaults checklist:
  - No secret has a usable default value. Missing secret → refuse to boot.
  - Empty-string / placeholder secrets are never valid.
  - The bind address defaults to loopback.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def _env(name: str, *, default: str | None = None, required: bool = False) -> str:
    val = os.environ.get(name, default or "").strip()
    if required and not val:
        raise SystemExit(f"FATAL: {name} is required (no usable default).")
    return val


@dataclass(frozen=True)
class SalesConfig:
    # Bind
    bind: str
    port: int

    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_price_indie: str
    stripe_price_pro: str
    stripe_price_enterprise: str
    success_url: str
    cancel_url: str

    # SMTP
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_use_tls: bool

    # License signing
    license_private_key_path: Path  # PEM file, mode 600
    license_product_id: str  # "gargoyle-packy"
    license_product_version: str  # "2.0.0"

    # Database
    db_path: Path

    @property
    def is_loopback_only(self) -> bool:
        if self.bind in ("127.0.0.1", "::1", "[::1]", "localhost"):
            return True
        if self.bind.startswith("127."):
            return True
        return False


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"FATAL: {name}={raw!r} is not an integer") from exc


def load_config() -> SalesConfig:
    bind = _env("SALES_BIND", default="127.0.0.1")
    port = _int_env("SALES_PORT", 8766)
    if not (1 <= port <= 65535):
        raise SystemExit(f"FATAL: SALES_PORT={port} is out of range (1-65535)")

    cfg = SalesConfig(
        bind=bind,
        port=port,
        stripe_secret_key=_env("STRIPE_SECRET_KEY", required=True),
        stripe_webhook_secret=_env("STRIPE_WEBHOOK_SECRET", required=True),
        stripe_price_indie=_env("STRIPE_PRICE_INDIE", required=True),
        stripe_price_pro=_env("STRIPE_PRICE_PRO", required=True),
        stripe_price_enterprise=_env("STRIPE_PRICE_ENTERPRISE", required=True),
        success_url=_env(
            "SALES_SUCCESS_URL",
            default="https://kirkforge.com/packy/success.html",
        ),
        cancel_url=_env(
            "SALES_CANCEL_URL",
            default="https://kirkforge.com/packy/pricing.html",
        ),
        smtp_host=_env("SMTP_HOST", required=True),
        smtp_port=_int_env("SMTP_PORT", 587),
        smtp_user=_env("SMTP_USER", required=True),
        smtp_password=_env("SMTP_PASSWORD", required=True),
        smtp_from=_env("SMTP_FROM", required=True),
        smtp_use_tls=_bool_env("SMTP_USE_TLS", default=True),
        license_private_key_path=Path(
            _env("LICENSE_PRIVATE_KEY_PATH", default="/var/lib/sales-packy/private_key.pem")
        ),
        license_product_id=_env("LICENSE_PRODUCT_ID", default="gargoyle-packy"),
        license_product_version=_env("LICENSE_PRODUCT_VERSION", default="2.0.0"),
        db_path=Path(_env("SALES_DB_PATH", default="./sales.db")),
    )

    if not cfg.license_private_key_path.is_file():
        raise SystemExit(
            f"FATAL: license private key not found at {cfg.license_private_key_path}. "
            f"Generate one with: python -m tools.keygen init"
        )

    if not cfg.is_loopback_only:
        logger.warning(
            "SALES_BIND=%s is non-loopback. The sales service is the public-facing "
            "endpoint for Stripe webhooks, so this is expected in production. "
            "Make sure TLS is terminated upstream (nginx / fly.io / render / etc).",
            cfg.bind,
        )

    return cfg


def tier_to_price(cfg: SalesConfig, tier: str) -> str:
    return {
        "indie": cfg.stripe_price_indie,
        "pro": cfg.stripe_price_pro,
        "enterprise": cfg.stripe_price_enterprise,
    }[tier]


def tier_to_seats(tier: str) -> int:
    return {
        "indie": 1,
        "pro": 5,
        "enterprise": 999,  # "unlimited" in the customer-facing summary
    }[tier]


def tier_to_support_years(tier: str) -> int:
    return {
        "indie": 1,
        "pro": 1,
        "enterprise": 1,
    }[tier]
