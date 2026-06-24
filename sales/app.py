"""FastAPI app factory for the sales service.

Wire order (FastAPI):
  1. Load config (env-driven, fail-closed)
  2. Open DB (SQLite, file mode 600)
  3. Load signing key (PEM, mode 600 in production)
  4. Build emailer (SMTP)
  5. Mount routes

The sales service is public-facing (Stripe webhooks come in from
the internet), so we DON'T bind to loopback by default in production
— but we DO require a webhook secret, and we DO verify the signature.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI

from sales.config import SalesConfig, load_config
from sales.db import LicenseDB
from sales.emailer import SMTPEmailer
from sales.license_signer import LicenseSigner
from sales.routes import checkout as checkout_routes
from sales.routes import portal as portal_routes
from sales.routes import webhook as webhook_routes

logger = logging.getLogger(__name__)


def create_app(
    *,
    config: SalesConfig | None = None,
    db: LicenseDB | None = None,
    signer: LicenseSigner | None = None,
    emailer=None,
    checkout_factory=None,
) -> FastAPI:
    """Build the app. All dependencies are injectable for tests."""
    cfg = config or load_config()
    license_db = db or LicenseDB(cfg.db_path)
    license_signer = signer or LicenseSigner(cfg.license_private_key_path)
    mailer = emailer if emailer is not None else SMTPEmailer(
        host=cfg.smtp_host,
        port=cfg.smtp_port,
        user=cfg.smtp_user,
        password=cfg.smtp_password,
        from_addr=cfg.smtp_from,
        use_tls=cfg.smtp_use_tls,
    )

    app = FastAPI(
        title="KirkForge Sales",
        description="Stripe Checkout + license signing + customer portal",
        version="0.1.0",
    )

    # /healthz is unauthenticated. Load balancers ping it.
    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True, "service": "sales"}

    # Wire routes. Each module gets the dependencies it needs as a closure.
    checkout_routes.mount(
        app,
        cfg=cfg,
        checkout_factory=checkout_factory,
    )
    webhook_routes.mount(
        app,
        cfg=cfg,
        db=license_db,
        signer=license_signer,
        emailer=mailer,
    )
    portal_routes.mount(
        app,
        db=license_db,
    )

    return app
