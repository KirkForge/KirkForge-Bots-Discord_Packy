"""License module unit tests for Gargoyle Packy.

Covers:
  - manifest sign/verify round-trip
  - tampered claims rejected
  - wrong public key rejected
  - placeholder key refuses to verify
  - product mismatch (The Specialist license) rejected
  - tier_includes returns expected set for each Packy tier
  - load() finds license in tmp_path

Run: pytest tests/test_license.py -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import license.keys as license_keys_mod
from license import (
    FEATURE_ADVANCED_LORE,
    FEATURE_CHAOS_LAYER,
    FEATURE_CORE_CHARACTER,
    FEATURE_CUSTOM_PERSONA,
    FEATURE_DISCORD_BOT,
    FEATURE_MICROSERVICE_MODE,
    FEATURE_MULTI_GUILD,
    FEATURE_PRIORITY_SUPPORT,
    FEATURE_SLA,
    FEATURE_SOURCE_CODE,
    PRODUCT_ID,
    TIER_COMMUNITY,
    TIER_ENTERPRISE,
    TIER_FEATURES,
    TIER_INDIE,
    TIER_PRO,
    LicenseNotFoundError,
    LicenseProductMismatchError,
    LicenseSignatureError,
    load,
    tier_includes,
)
from license.errors import LicenseFormatError

from conftest import make_signed_license, write_license_to


# --- Sanity: product is "gargoyle-packy" ---------------------------------

def test_product_id_is_packy():
    assert PRODUCT_ID == "gargoyle-packy"


def test_default_tiers_present():
    assert TIER_COMMUNITY in TIER_FEATURES
    assert TIER_INDIE in TIER_FEATURES
    assert TIER_PRO in TIER_FEATURES
    assert TIER_ENTERPRISE in TIER_FEATURES


# --- Tier feature map ----------------------------------------------------

def test_community_tier_basics():
    # Community is the eval tier: character + discord bot only.
    assert tier_includes(TIER_COMMUNITY, FEATURE_CORE_CHARACTER)
    assert tier_includes(TIER_COMMUNITY, FEATURE_DISCORD_BOT)
    assert not tier_includes(TIER_COMMUNITY, FEATURE_MICROSERVICE_MODE)
    assert not tier_includes(TIER_COMMUNITY, FEATURE_MULTI_GUILD)
    assert not tier_includes(TIER_COMMUNITY, FEATURE_PRIORITY_SUPPORT)


def test_indie_tier_unlocks_microservice():
    # Indie adds microservice mode + chaos layer.
    assert tier_includes(TIER_INDIE, FEATURE_MICROSERVICE_MODE)
    assert tier_includes(TIER_INDIE, FEATURE_CHAOS_LAYER)
    assert not tier_includes(TIER_INDIE, FEATURE_MULTI_GUILD)
    assert not tier_includes(TIER_INDIE, FEATURE_CUSTOM_PERSONA)


def test_pro_tier_unlocks_multi_guild_and_custom_persona():
    assert tier_includes(TIER_PRO, FEATURE_MULTI_GUILD)
    assert tier_includes(TIER_PRO, FEATURE_CUSTOM_PERSONA)
    assert tier_includes(TIER_PRO, FEATURE_ADVANCED_LORE)
    assert tier_includes(TIER_PRO, FEATURE_PRIORITY_SUPPORT)
    assert not tier_includes(TIER_PRO, FEATURE_SOURCE_CODE)
    assert not tier_includes(TIER_PRO, FEATURE_SLA)


def test_enterprise_unlocks_source_and_sla():
    assert tier_includes(TIER_ENTERPRISE, FEATURE_SOURCE_CODE)
    assert tier_includes(TIER_ENTERPRISE, FEATURE_SLA)
    # Enterprise is a superset of pro
    for f in TIER_FEATURES[TIER_PRO]:
        assert tier_includes(TIER_ENTERPRISE, f)


# --- Sign / verify round trip -------------------------------------------

def test_signed_license_loads_cleanly(license_keypair, tmp_path):
    priv, _pub = license_keypair
    license_dict = make_signed_license(priv, tier=TIER_PRO)
    path = tmp_path / "license.json"
    write_license_to(path, license_dict)

    loaded = load(path=path)
    assert loaded.license_id.startswith("KFG-")
    assert loaded.tier == TIER_PRO
    assert loaded.customer_name == "Test Co"


def test_tampered_claims_rejected(license_keypair, tmp_path):
    priv, _ = license_keypair
    license_dict = make_signed_license(priv, tier=TIER_INDIE)
    license_dict["tier"] = TIER_ENTERPRISE  # try to elevate
    path = tmp_path / "license.json"
    write_license_to(path, license_dict)

    with pytest.raises(LicenseSignatureError):
        load(path=path)


def test_wrong_public_key_rejected(tmp_path, monkeypatch):
    # Sign with key A
    priv_a = Ed25519PrivateKey.generate()
    license_dict = make_signed_license(priv_a, tier=TIER_PRO)
    path = tmp_path / "license.json"
    write_license_to(path, license_dict)

    # Embed key B in the product
    priv_b = Ed25519PrivateKey.generate()
    monkeypatch.setattr(
        license_keys_mod, "PUBLIC_KEY_RAW", priv_b.public_key().public_bytes_raw()
    )

    with pytest.raises(LicenseSignatureError):
        load(path=path)


def test_specialist_license_rejected_on_packy(license_keypair, tmp_path):
    """A license signed for the right key but the wrong product is rejected
    before any tier check — the loader refuses product-mismatch first."""
    priv, _ = license_keypair
    license_dict = make_signed_license(priv, product="the-specialist", tier=TIER_PRO)
    path = tmp_path / "license.json"
    write_license_to(path, license_dict)

    with pytest.raises(LicenseProductMismatchError) as exc:
        load(path=path)
    assert "gargoyle-packy" in str(exc.value)


def test_placeholder_public_key_refuses_to_verify(tmp_path, monkeypatch):
    # Restore the placeholder (all-zeros) key — the license was signed
    # with a real key, so verification will fail.
    monkeypatch.setattr(license_keys_mod, "PUBLIC_KEY_RAW", bytes(32))
    priv = Ed25519PrivateKey.generate()
    license_dict = make_signed_license(priv, tier=TIER_PRO)
    path = tmp_path / "license.json"
    write_license_to(path, license_dict)

    with pytest.raises(LicenseSignatureError):
        load(path=path)


def test_garbage_signature_rejected(license_keypair, tmp_path):
    priv, _ = license_keypair
    license_dict = make_signed_license(priv, tier=TIER_PRO)
    license_dict["signature"] = "not-base64-!@#$"
    path = tmp_path / "license.json"
    write_license_to(path, license_dict)

    with pytest.raises((LicenseSignatureError, LicenseFormatError)):
        load(path=path)


def test_missing_signature_rejected(license_keypair, tmp_path):
    priv, _ = license_keypair
    license_dict = make_signed_license(priv, tier=TIER_PRO)
    license_dict["signature"] = ""
    path = tmp_path / "license.json"
    write_license_to(path, license_dict)

    with pytest.raises((LicenseSignatureError, LicenseFormatError)):
        load(path=path)


# --- load() not-found ----------------------------------------------------

def test_load_raises_when_no_license_anywhere(monkeypatch, tmp_path):
    # Run from a tmp dir + override env to guarantee nothing is found
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PACKY_LICENSE_PATH", str(tmp_path / "no-such-license.json"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "no-such-config"))

    with pytest.raises(LicenseNotFoundError) as exc:
        load()
    assert "gargoyle-packy" in str(exc.value).lower() or "license" in str(exc.value).lower()


# --- require_feature -----------------------------------------------------

def test_require_feature_fails_closed_when_no_license_loaded():
    import license as lic
    saved = lic.current
    lic.current = None
    try:
        from license import LicenseFeatureUnavailable, require_feature
        with pytest.raises(LicenseFeatureUnavailable):
            require_feature(FEATURE_DISCORD_BOT)
    finally:
        lic.current = saved
