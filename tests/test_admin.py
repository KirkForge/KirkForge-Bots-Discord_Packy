"""Admin endpoint smoke tests for packy_endpoint.py.

Verifies that the new /admin/* routes (license, version, update) are
mounted, parse the embedded license correctly, and return the expected
shape. Uses TestClient to bypass the real uvicorn startup event
(no actual port binding).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

import license.keys as license_keys_mod
import license as lic_mod

from conftest import make_signed_license, write_license_to


# Project root on sys.path so imports resolve to gargoyle-packy/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def client(monkeypatch, tmp_path):
    """Build a TestClient for the Packy FastAPI app.

    The startup event runs boot_license() which calls sys.exit(1) on
    failure — so we have to seed a valid license on disk first, AND
    patch the embedded public key to match.

    Auth gate: set PACKY_API_SECRET so the module-level check doesn't exit,
    and send a Bearer token with every request.
    """
    _TEST_SECRET = "test-admin-secret-at-least-32-chars"
    monkeypatch.setenv("PACKY_API_SECRET", _TEST_SECRET)

    priv = Ed25519PrivateKey.generate()
    monkeypatch.setattr(license_keys_mod, "PUBLIC_KEY_RAW", priv.public_key().public_bytes_raw())
    license_dict = make_signed_license(priv, tier="pro")
    license_path = tmp_path / "license.json"
    write_license_to(license_path, license_dict)
    monkeypatch.setenv("PACKY_LICENSE_PATH", str(license_path))

    # Import the module fresh so the monkeypatched key is in effect.
    # Clear the lru_cache / module if needed.
    if "src.orchestration.packy_endpoint" in sys.modules:
        del sys.modules["src.orchestration.packy_endpoint"]
    from src.orchestration import packy_endpoint

    # The startup event re-sets license.current. Run it manually so
    # /admin/license has something to return.
    packy_endpoint.boot_license()

    with TestClient(packy_endpoint.app, headers={"Authorization": f"Bearer {_TEST_SECRET}"}) as c:
        # The TestClient context manager triggers startup events, so
        # boot_license() will run AGAIN. We could skip the manual call
        # above, but having both ensures a clean state.
        yield c


def test_admin_version_returns_product_and_version(client):
    r = client.get("/admin/version")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["product"] == "gargoyle-packy"
    assert body["version"]  # non-empty


def test_admin_license_returns_loaded_license(client):
    r = client.get("/admin/license")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tier"] == "pro"
    assert body["customer_name"] == "Test Co"
    assert body["support_active"] is True
    assert body["source_path"]


def test_admin_license_503_when_no_license_loaded(monkeypatch, tmp_path):
    # Build a fresh app with no license present. Patch boot_license to
    # a no-op so the lifespan startup event doesn't sys.exit(1) — we
    # want the route handler to actually run and return 503.
    _TEST_SECRET = "test-admin-secret-at-least-32-chars"
    monkeypatch.setenv("PACKY_API_SECRET", _TEST_SECRET)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PACKY_LICENSE_PATH", str(tmp_path / "no-license.json"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "no-cfg"))

    if "src.orchestration.packy_endpoint" in sys.modules:
        del sys.modules["src.orchestration.packy_endpoint"]
    from src.orchestration import packy_endpoint

    monkeypatch.setattr(packy_endpoint, "boot_license", lambda: None)
    lic_mod.current = None

    with TestClient(packy_endpoint.app, headers={"Authorization": f"Bearer {_TEST_SECRET}"}) as c:
        r = c.get("/admin/license")
        assert r.status_code == 503
        assert "no license loaded" in r.json()["detail"].lower()
    # Reset for other tests
    lic_mod.current = None


def test_admin_update_returns_updatecheck_shape(client, monkeypatch):
    """The /admin/update endpoint surfaces the update channel result.
    Without a real manifest URL it should report a network error (the
    default URL points at GitHub which isn't reachable in this test),
    but the response shape must be UpdateCheck-shaped."""
    r = client.get("/admin/update")
    assert r.status_code == 200, r.text
    body = r.json()
    # UpdateCheck fields
    for k in ("current_version", "available", "signature_ok", "checked_at", "manifest_url"):
        assert k in body
    # No network → error populated, no upgrade command
    assert body["upgrade_command"] is None
    assert body["signature_ok"] is False
    assert body["error"]
