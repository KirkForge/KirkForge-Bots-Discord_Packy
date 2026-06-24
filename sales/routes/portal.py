"""Customer portal — re-download your license.

Auth model: the buyer's email is the secret they already received in
their purchase confirmation. The portal login requires both
`license_id` and `customer_email`; we look up the row, constant-time
compare the email, and serve the license JSON for download.

This is NOT a high-security portal — there's no password reset, no
rate-limiting beyond an in-memory counter. The threat model is "someone
finds /portal and tries random IDs", not "someone is brute-forcing
real email addresses". For higher security, we'd plug in magic-link
email auth. That's a future task.
"""

from __future__ import annotations

import hmac
import logging
import threading
import time
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from sales.db import LicenseDB

logger = logging.getLogger(__name__)


# --- Rate limiter ---------------------------------------------------------

class _RateLimiter:
    """In-memory token bucket per (ip, route).

    5 attempts per 15 minutes per IP. Good enough for a portal that
    gets <1000 unique visitors/month. For higher traffic, swap for
    Redis-backed limiter; the interface stays the same.
    """

    WINDOW_SECONDS = 15 * 60
    MAX_ATTEMPTS = 5

    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        """Return True if the request is allowed, False if it should be 429'd."""
        now = time.monotonic()
        with self._lock:
            attempts = self._buckets[key]
            cutoff = now - self.WINDOW_SECONDS
            self._buckets[key] = [t for t in attempts if t >= cutoff]
            if len(self._buckets[key]) >= self.MAX_ATTEMPTS:
                return False
            self._buckets[key].append(now)
            return True


_RATE = _RateLimiter()


# --- HTML templates -------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
from fastapi.templating import Jinja2Templates  # noqa: E402
TEMPLATES = Jinja2Templates(directory=str(_TEMPLATES_DIR))


# --- Mount ----------------------------------------------------------------

def mount(app, *, db: LicenseDB) -> None:
    router = APIRouter()

    @router.get("/portal", response_class=HTMLResponse)
    def portal_login_form(request: Request, license_id: str = "") -> Response:
        return TEMPLATES.TemplateResponse(
            "portal_login.html",
            {"request": request, "license_id": license_id, "error": None},
        )

    @router.post("/portal", response_class=HTMLResponse)
    def portal_login_submit(
        request: Request,
        license_id: str = Form(...),
        email: str = Form(...),
    ) -> Response:
        # Rate limit per IP.
        client_ip = request.client.host if request.client else "unknown"
        if not _RATE.check(f"portal:{client_ip}"):
            return TEMPLATES.TemplateResponse(
                "portal_login.html",
                {"request": request, "license_id": license_id,
                 "error": "Too many attempts. Try again in 15 minutes."},
                status_code=429,
            )
        license_id = license_id.strip()
        email = email.strip().lower()
        if not license_id or not email:
            return TEMPLATES.TemplateResponse(
                "portal_login.html",
                {"request": request, "license_id": license_id,
                 "error": "Both fields are required."},
                status_code=400,
            )

        row = db.find_by_license_id(license_id)
        # Constant-time compare on the email. We always do the lookup +
        # compare even if no row exists, so timing doesn't leak which
        # license_ids are valid.
        if row is None:
            hmac.compare_digest(email, "")
            return TEMPLATES.TemplateResponse(
                "portal_login.html",
                {"request": request, "license_id": license_id,
                 "error": "License not found, or email does not match."},
                status_code=404,
            )
        # We treat the email check as the secret: if it matches, the
        # customer gets in. Constant-time compare defends against
        # timing attacks on the email field.
        if not hmac.compare_digest(email, row.customer_email.lower()):
            return TEMPLATES.TemplateResponse(
                "portal_login.html",
                {"request": request, "license_id": license_id,
                 "error": "License not found, or email does not match."},
                status_code=404,
            )

        # Success — render the download page with the license metadata.
        return TEMPLATES.TemplateResponse(
            "portal_download.html",
            {
                "request": request,
                "license_id": row.license_id,
                "tier": row.tier,
                "customer_name": row.customer_name,
                "customer_email": row.customer_email,
                "support_until": row.support_until,
                "seats": row.seats,
                "features": row.features,
            },
        )

    @router.get("/portal/{license_id}/download")
    def portal_download(license_id: str, request: Request) -> Response:
        """Programmatic download endpoint. Same email-gate as the form.

        The customer passes their email as a query param. This lets a
        CLI download script (or a curl one-liner) work without browser
        interaction. We use the same constant-time compare.
        """
        client_ip = request.client.host if request.client else "unknown"
        if not _RATE.check(f"portal-dl:{client_ip}"):
            raise HTTPException(status_code=429, detail="Too many attempts.")
        email = (request.query_params.get("email") or "").strip().lower()
        if not email:
            raise HTTPException(status_code=400, detail="email query param required")
        row = db.find_by_license_id(license_id)
        if row is None or not hmac.compare_digest(email, row.customer_email.lower()):
            raise HTTPException(status_code=404, detail="not found")
        return Response(
            content=row.license_json,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="license-{license_id}.json"',
            },
        )

    app.include_router(router)
