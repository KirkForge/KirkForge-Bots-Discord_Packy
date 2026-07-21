"""POST /webhook/stripe — receives Stripe events, signs licenses.

Security boundary: Stripe posts the event with a `Stripe-Signature`
header. We MUST verify it before doing anything. We do this with the
official `stripe.Webhook.construct_event`, which uses the webhook
signing secret in `STRIPE_WEBHOOK_SECRET` to verify the HMAC-SHA256.

Without that, anyone who knows the URL could POST a fake
`checkout.session.completed` and trigger a license signing.
"""

from __future__ import annotations

import json
import logging

import stripe
from fastapi import APIRouter, HTTPException, Request

from sales.config import SalesConfig
from sales.db import DuplicateSessionError, LicenseDB, LicenseRow, now_utc_iso
from sales.license_signer import LicenseSigner, SignRequest
from sales.routes.checkout import price_id_to_tier

logger = logging.getLogger(__name__)


def mount(app, *, cfg: SalesConfig, db: LicenseDB, signer: LicenseSigner, emailer) -> None:
    router = APIRouter()

    @router.post("/webhook/stripe")
    async def stripe_webhook(request: Request) -> dict:
        # Read the body as bytes. The Stripe SDK signature check needs
        # the exact bytes Stripe sent; do NOT re-serialize through JSON.
        body = await request.body()
        sig_header = request.headers.get("stripe-signature", "")

        try:
            event = stripe.Webhook.construct_event(
                body,
                sig_header,
                cfg.stripe_webhook_secret,
            )
        except ValueError:
            # body wasn't valid JSON
            raise HTTPException(status_code=400, detail="invalid payload")
        except stripe.error.SignatureVerificationError:
            # HMAC mismatch — the request didn't come from Stripe, or
            # the body was tampered with in flight.
            logger.warning("stripe webhook signature verification failed")
            raise HTTPException(status_code=400, detail="signature verification failed")

        # Stripe SDK v7+ returns typed objects — use attribute access.
        if event.type != "checkout.session.completed":
            return {"received": True, "handled": False, "type": event.type}

        session = event.data.object
        return await _handle_completed(
            cfg=cfg,
            db=db,
            signer=signer,
            emailer=emailer,
            session=session,
        )

    app.include_router(router)


async def _handle_completed(*, cfg, db, signer, emailer, session) -> dict:
    # Stripe SDK returns typed objects; support both dict-style (for
    # tests using raw JSON) and attribute-style (for the real SDK).
    def _get(obj, *path, default=""):
        cur = obj
        for key in path:
            if cur is None:
                return default
            if isinstance(cur, dict):
                cur = cur.get(key)
            else:
                cur = getattr(cur, key, None)
        return cur if cur is not None else default

    session_id = _get(session, "id")
    if not session_id:
        logger.error("checkout.session.completed without id: %r", session)
        raise HTTPException(status_code=400, detail="session has no id")

    # Idempotency: if we've already processed this session, ack and move on.
    existing = db.find_by_session_id(session_id)
    if existing:
        logger.info("stripe session %s already processed, skipping", session_id)
        return {"received": True, "handled": True, "license_id": existing.license_id}

    # Resolve the tier from the session. We stored the tier in metadata
    # when we created the Checkout session; that's the trusted path.
    tier = _get(session, "metadata", "tier")
    if not tier:
        # Resolve price_id from line_items (object or dict)
        if isinstance(session, dict):
            price_id = (
                (session.get("line_items") or {})
                .get("data", [{}])[0]
                .get("price", {})
                .get("id", "")
            )
        else:
            li = getattr(session, "line_items", None)
            if li and getattr(li, "data", None):
                price_id = li.data[0].price.id
            else:
                price_id = ""
        tier = _tier_from_price_id(cfg, price_id)
    if not tier:
        logger.error("could not determine tier for session %s", session_id)
        raise HTTPException(status_code=400, detail="tier unresolved")

    # customer_details is what the buyer typed in the checkout form.
    customer_email = _get(session, "customer_details", "email").strip()
    raw_name = _get(session, "customer_details", "name")
    customer_name = (raw_name or customer_email.split("@")[0] or "Customer").strip()
    if not customer_email:
        logger.error("no email on session %s", session_id)
        raise HTTPException(status_code=400, detail="no email on session")

    amount = int(_get(session, "amount_total", default=0))
    currency = _get(session, "currency", default="usd")

    sign_req = SignRequest(
        tier=tier,
        customer_name=customer_name,
        customer_email=customer_email,
        product_id=cfg.license_product_id,
        product_version=cfg.license_product_version,
    )
    result = signer.sign(sign_req)

    row = LicenseRow(
        license_id=result.license_id,
        tier=tier,
        customer_name=customer_name,
        customer_email=customer_email,
        stripe_session_id=session_id,
        signed_at=now_utc_iso(),
        support_until=result.support_until.isoformat(),
        seats=result.seats,
        features_json=json.dumps(result.features),
        license_json=result.license_json,
        amount_cents=amount,
        currency=currency,
    )
    try:
        db.insert_license(row)
    except DuplicateSessionError:
        # Lost the race with a concurrent webhook delivery. Fine.
        logger.info("concurrent webhook for %s, skipping", session_id)
        return {"received": True, "handled": True, "license_id": result.license_id}

    portal_url = cfg.success_url.rsplit("/", 1)[0] + f"/portal?license_id={result.license_id}"
    try:
        emailer.send_license(
            to_email=customer_email,
            customer_name=customer_name,
            tier=tier,
            license_id=result.license_id,
            license_json=result.license_json,
            portal_url=portal_url,
        )
    except Exception:
        # Email is a nice-to-have; the license is already in the DB and
        # the customer can re-download from the portal. Log and move on.
        logger.exception("license email send failed for %s", result.license_id)

    logger.info(
        "license signed: tier=%s license_id=%s customer=%s",
        tier,
        result.license_id,
        customer_email,
    )
    return {"received": True, "handled": True, "license_id": result.license_id}


def _tier_from_price_id(cfg: SalesConfig, price_id: str) -> str:
    try:
        return price_id_to_tier(cfg, price_id)
    except ValueError:
        return ""
