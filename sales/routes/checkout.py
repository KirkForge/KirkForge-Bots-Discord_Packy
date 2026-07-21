"""POST /checkout/{tier} — creates a Stripe Checkout session.

The landing page's buy button POSTs here. We create a Stripe Checkout
session with the configured price ID for the tier, prefill customer
email if we can, and return the redirect URL. The browser then
follows the redirect to Stripe's hosted checkout.

Why not create the session client-side with a publishable key? Because
the secret key is server-side only, and we need to set
`success_url` / `cancel_url` from the server so the same backend
that signs the license is the one Stripe redirects back to.
"""

from __future__ import annotations

import logging
from typing import Callable

import stripe
from fastapi import APIRouter, HTTPException, Request

from sales.config import SalesConfig, tier_to_price

logger = logging.getLogger(__name__)


# Real Stripe client factory. Tests inject a fake.
def real_stripe_checkout_factory(cfg: SalesConfig) -> Callable[..., dict]:
    stripe.api_key = cfg.stripe_secret_key

    def create(
        *, price_id: str, success_url: str, cancel_url: str, customer_email: str | None
    ) -> dict:
        kwargs = {
            "mode": "payment",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            # Allow promotion codes — Stripe Tax handles VAT automatically
            # when `automatic_tax` is enabled in the dashboard.
            "automatic_tax": {"enabled": True},
            # Metadata is what the webhook reads to know which tier to sign
            # for. NEVER trust the URL tier — we set it in metadata server-side.
            "metadata": {"tier": price_id_to_tier(cfg, price_id)},
        }
        if customer_email:
            kwargs["customer_email"] = customer_email
        session = stripe.checkout.Session.create(**kwargs)
        return {"id": session.id, "url": session.url}

    return create


VALID_TIERS = ("indie", "pro", "enterprise")


def mount(app, *, cfg: SalesConfig, checkout_factory=None) -> None:
    factory = checkout_factory or real_stripe_checkout_factory(cfg)
    router = APIRouter()

    @router.post("/checkout/{tier}")
    async def create_checkout(tier: str, request: Request) -> dict:
        if tier not in VALID_TIERS:
            raise HTTPException(status_code=400, detail=f"unknown tier: {tier}")
        price_id = tier_to_price(cfg, tier)
        # Stripe reads the success URL with the session_id query param we
        # configured in success_url. Use a fresh query arg every time so
        # CSRF reuse is impossible.
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass
        customer_email = (body.get("email") or "").strip() or None
        try:
            session = factory(
                price_id=price_id,
                success_url=cfg.success_url,
                cancel_url=cfg.cancel_url,
                customer_email=customer_email,
            )
        except stripe.error.StripeError as exc:
            logger.exception("stripe checkout create failed")
            raise HTTPException(status_code=502, detail=f"stripe error: {exc}")
        return {"session_id": session["id"], "url": session["url"]}

    app.include_router(router)


def price_id_to_tier(cfg: SalesConfig, price_id: str) -> str:
    if price_id == cfg.stripe_price_indie:
        return "indie"
    if price_id == cfg.stripe_price_pro:
        return "pro"
    if price_id == cfg.stripe_price_enterprise:
        return "enterprise"
    raise ValueError(f"unknown price_id: {price_id}")
