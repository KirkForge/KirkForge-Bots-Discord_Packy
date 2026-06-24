"""Sales service smoke tests for Gargoyle Packy.

Hermetic: no Stripe, no SMTP. Validates:
  - config loads with required env vars
  - emailer builds the right subject + body for Packy
  - license_signer round-trips a claim through Packy features
  - DB writes/reads license rows
  - tier → price + seat mapping for Packy tiers
"""

from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Project root on sys.path so the imports below resolve to gargoyle-packy/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# --- SalesConfig ---------------------------------------------------------

def test_sales_config_requires_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("SALES_DB_PATH", str(tmp_path / "sales.db"))
    # Missing STRIPE_SECRET_KEY etc. — should refuse to boot.
    with pytest.raises(SystemExit) as exc:
        from sales.config import load_config
        load_config()
    assert "STRIPE_SECRET_KEY" in str(exc.value)


def test_sales_config_loads_with_full_env(monkeypatch, tmp_path):
    # Make a real key file so the config's private-key check passes.
    key_path = tmp_path / "private_key.pem"
    key_path.write_bytes(b"\x00" * 32)  # placeholder

    monkeypatch.setenv("SALES_BIND", "127.0.0.1")
    monkeypatch.setenv("SALES_PORT", "8767")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    monkeypatch.setenv("STRIPE_PRICE_INDIE", "price_indie")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_pro")
    monkeypatch.setenv("STRIPE_PRICE_ENTERPRISE", "price_ent")
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_USER", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pw")
    monkeypatch.setenv("SMTP_FROM", "licenses-packy@test")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("LICENSE_PRIVATE_KEY_PATH", str(key_path))
    monkeypatch.setenv("SALES_DB_PATH", str(tmp_path / "sales.db"))

    from sales.config import load_config
    cfg = load_config()
    assert cfg.license_product_id == "gargoyle-packy"
    assert cfg.license_product_version == "2.0.0"
    assert cfg.is_loopback_only is True
    assert cfg.port == 8767


def test_tier_to_price_for_packy(monkeypatch, tmp_path):
    key_path = tmp_path / "private_key.pem"
    key_path.write_bytes(b"\x00" * 32)

    monkeypatch.setenv("SALES_BIND", "127.0.0.1")
    monkeypatch.setenv("SALES_PORT", "8767")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    monkeypatch.setenv("STRIPE_PRICE_INDIE", "price_indie")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_pro")
    monkeypatch.setenv("STRIPE_PRICE_ENTERPRISE", "price_ent")
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_USER", "u")
    monkeypatch.setenv("SMTP_PASSWORD", "p")
    monkeypatch.setenv("SMTP_FROM", "x")
    monkeypatch.setenv("LICENSE_PRIVATE_KEY_PATH", str(key_path))
    monkeypatch.setenv("SALES_DB_PATH", str(tmp_path / "sales.db"))

    from sales.config import load_config, tier_to_price
    cfg = load_config()
    assert tier_to_price(cfg, "indie") == "price_indie"
    assert tier_to_price(cfg, "pro") == "price_pro"
    assert tier_to_price(cfg, "enterprise") == "price_ent"


# --- Emailer: builds Packy subject + body --------------------------------

def test_emailer_subject_and_body_mention_packy():
    from sales.emailer import FakeEmailer
    e = FakeEmailer()
    e.send_license(
        to_email="customer@example.com",
        customer_name="Customer",
        tier="pro",
        license_id="KFG-PROD-AB12CD34",
        license_json='{"license_id":"KFG-PROD-AB12CD34"}',
        portal_url="https://sales.kirkforge.com/packy/portal",
    )
    assert len(e.sent) == 1
    msg = e.sent[0]
    assert "Gargoyle Packy pro license" in msg["Subject"]
    # The email is multipart (has a license.json attachment), so get_content()
    # raises. Walk the parts and grab the plain-text one.
    body = None
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            body = part.get_content()
            break
    assert body is not None
    assert "Gargoyle Packy" in body
    assert "KFG-PROD-AB12CD34" in body
    assert "kirkforge/packy/license.json" in body


# --- DB: writes/reads ----------------------------------------------------

def test_db_insert_and_find_by_license_id(tmp_path):
    from sales.db import LicenseDB, LicenseRow
    db = LicenseDB(tmp_path / "sales.db")
    row = LicenseRow(
        license_id="KFG-PROD-AB12CD34",
        tier="pro",
        customer_name="Test",
        customer_email="t@example.com",
        stripe_session_id="cs_test_1",
        signed_at=datetime.now(timezone.utc).isoformat(),
        support_until=datetime.now(timezone.utc).isoformat(),
        seats=5,
        features_json='["core_character","discord_bot","microservice_mode"]',
        license_json="{}",
        amount_cents=99900,
        currency="usd",
    )
    db.insert_license(row)
    found = db.find_by_license_id("KFG-PROD-AB12CD34")
    assert found is not None
    assert found.tier == "pro"
    assert found.features == ["core_character", "discord_bot", "microservice_mode"]


def test_db_idempotent_on_duplicate_session(tmp_path):
    from sales.db import DuplicateSessionError, LicenseDB, LicenseRow
    db = LicenseDB(tmp_path / "sales.db")
    common = dict(
        license_id="KFG-PROD-IDEM",
        tier="indie",
        customer_name="T",
        customer_email="t@x.com",
        stripe_session_id="cs_dup_1",
        signed_at=datetime.now(timezone.utc).isoformat(),
        support_until=datetime.now(timezone.utc).isoformat(),
        seats=1,
        features_json="[]",
        license_json="{}",
        amount_cents=19900,
        currency="usd",
    )
    db.insert_license(LicenseRow(**common))
    with pytest.raises(DuplicateSessionError):
        db.insert_license(LicenseRow(**common))


# --- LicenseSigner: end-to-end with Packy product id ---------------------

def test_signer_uses_gargoyle_packy_product(monkeypatch, tmp_path):
    """Full round-trip: load a private key, sign a license for the
    Packy product, verify the signed blob against the matching public key."""
    from sales.license_signer import LicenseSigner, SignRequest
    from cryptography.hazmat.primitives import serialization

    # Generate a key and write it as PKCS8 PEM (matches what
    # tools.keygen emits and what the sales service LicenseSigner reads).
    priv = Ed25519PrivateKey.generate()
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_path = tmp_path / "private_key.pem"
    key_path.write_bytes(pem)

    # Patch the embedded product public key so the loader can verify.
    import license.keys as license_keys_mod
    monkeypatch.setattr(
        license_keys_mod, "PUBLIC_KEY_RAW", priv.public_key().public_bytes_raw()
    )

    signer = LicenseSigner(key_path)
    result = signer.sign(SignRequest(
        tier="pro",
        customer_name="Acme",
        customer_email="ops@acme.com",
        product_id="gargoyle-packy",
        product_version="2.0.0",
    ))

    # Write to disk and verify via the customer-side loader
    license_path = tmp_path / "license.json"
    license_path.write_text(result.license_json, encoding="utf-8")
    # Verify signature: re-parse and feed to the loader
    parsed = json.loads(result.license_json)
    assert parsed["product"] == "gargoyle-packy"
    assert parsed["tier"] == "pro"
    assert parsed["customer"]["name"] == "Acme"

    # The loader checks signature against the embedded public key (which
    # we patched). It should pass.
    from license import load as load_license
    loaded = load_license(path=license_path)
    assert loaded.claims.product == "gargoyle-packy"
    assert loaded.claims.tier == "pro"
    # The features should be the Packy pro tier's set, not The Specialist's
    assert "microservice_mode" in loaded.claims.features
    assert "multi_guild" in loaded.claims.features
    assert "voice_stt" not in loaded.claims.features  # not a Packy feature
