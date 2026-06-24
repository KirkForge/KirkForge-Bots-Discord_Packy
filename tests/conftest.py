"""Shared pytest fixtures for gargoyle-packy productization tests.

Hermetic: each test gets a fresh keypair via monkeypatch on the
embedded `license/keys.py` and `update/keys.py` PUBLIC_KEY_RAW. No
network, no real Stripe, no SMTP. License + manifest files go to
tmp_path only.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import license.keys as license_keys_mod
import license.loader as license_loader_mod
import update.keys as update_keys_mod
from license.claims import LICENSE_FORMAT_VERSION, Customer, LicenseClaims


# Project root on sys.path so `from license import ...` resolves to
# gargoyle-packy/license/ (not The_specialist/license/, which would
# cause product-mismatch errors).
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def license_keypair(monkeypatch):
    """Fresh Ed25519 keypair with the public half patched into the
    embedded `license.keys.PUBLIC_KEY_RAW`."""
    priv = Ed25519PrivateKey.generate()
    monkeypatch.setattr(license_keys_mod, "PUBLIC_KEY_RAW", priv.public_key().public_bytes_raw())
    return priv, priv.public_key()


@pytest.fixture()
def update_keypair(monkeypatch):
    """Fresh Ed25519 keypair with the public half patched into the
    embedded `update.keys.UPDATE_PUBLIC_KEY_RAW`."""
    priv = Ed25519PrivateKey.generate()
    monkeypatch.setattr(update_keys_mod, "UPDATE_PUBLIC_KEY_RAW", priv.public_key().public_bytes_raw())
    return priv, priv.public_key()


def make_signed_license(
    priv: Ed25519PrivateKey,
    *,
    tier: str = "pro",
    product: str = "gargoyle-packy",
    max_seats: int = 3,
    features: tuple[str, ...] = ("core_character", "discord_bot", "microservice_mode"),
    customer_name: str = "Test Co",
    customer_email: str = "ops@test.example",
    support_days: int = 365,
) -> dict:
    """Build and sign a LicenseClaims dict, suitable for writing to disk
    and feeding back into license.load()."""
    now = datetime.now(timezone.utc)
    claims = LicenseClaims(
        license_id=f"KFG-2026-TEST-{tier.upper()}",
        product=product,
        product_version="2.0.0",
        format_version=LICENSE_FORMAT_VERSION,
        customer=Customer(name=customer_name, email=customer_email),
        tier=tier,
        issued_at=now,
        support_until=now + timedelta(days=support_days),
        max_seats=max_seats,
        features=features,
    )
    payload_dict = claims.to_dict()
    payload = {k: v for k, v in payload_dict.items() if k != "signature"}
    sig = priv.sign(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    out = payload_dict
    out["signature"] = base64.b64encode(sig).decode("ascii")
    return out


def write_license_to(path: Path, license_dict: dict) -> None:
    path.write_text(json.dumps(license_dict, indent=2), encoding="utf-8")
