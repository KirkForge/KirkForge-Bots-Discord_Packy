"""Update-channel unit tests for Gargoyle Packy.

Covers:
  - manifest sign/verify round-trip
  - tampered claims rejected
  - wrong public key rejected
  - placeholder key refuses to verify
  - checker exposes upgrade_command only when signature_ok
  - checker surfaces network failures as structured errors
  - tools.keygen init-update creates a separate key file
  - tools.release sign-manifest + verify-manifest round-trip

Hermetic: monkeypatches urllib, generates fresh keypairs, no network.

Run: pytest tests/test_update.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import update.keys as update_keys_mod
from update.checker import check_for_update
from update.manifest import (
    DEFAULT_MANIFEST_URL,
    Manifest,
    ManifestVerificationError,
    sign_manifest,
    verify_manifest,
)


# --- Fixtures -------------------------------------------------------------

@pytest.fixture()
def update_keypair():
    priv = Ed25519PrivateKey.generate()
    return priv, priv.public_key()


@pytest.fixture()
def signed_manifest(update_keypair) -> Manifest:
    priv, _ = update_keypair
    return sign_manifest(
        Manifest(
            product="gargoyle-packy",
            version="2.0.1",
            released_at=datetime.now(timezone.utc).isoformat(),
            requires_support_active=True,
            upgrade_command="git pull && pip install -r gargoyle-packy/requirements.txt",
            changelog_url="https://github.com/.../CHANGELOG.md",
            min_python_version="3.11",
            notes="New persona tools, lore fixes.",
        ),
        priv,
    )


@pytest.fixture()
def patched_update_key(update_keypair, monkeypatch):
    """Point update.keys.UPDATE_PUBLIC_KEY_RAW at the test key's public half."""
    _, pub = update_keypair
    monkeypatch.setattr(
        update_keys_mod, "UPDATE_PUBLIC_KEY_RAW", pub.public_bytes_raw()
    )
    return pub


# --- Manifest sign/verify round trip -------------------------------------

def test_sign_then_verify_succeeds(update_keypair, signed_manifest):
    priv, pub = update_keypair
    verify_manifest(signed_manifest, public_key=pub)


def test_verify_uses_embedded_key_when_no_override(patched_update_key, signed_manifest):
    verify_manifest(signed_manifest)


def test_tampered_claims_rejected(patched_update_key, signed_manifest):
    # Attacker bumps the version without re-signing.
    bad = Manifest(**{**signed_manifest.to_dict(), "version": "9.9.9"})
    with pytest.raises(ManifestVerificationError):
        verify_manifest(bad)


def test_wrong_public_key_rejected(update_keypair, signed_manifest):
    other = Ed25519PrivateKey.generate().public_key()
    with pytest.raises(ManifestVerificationError):
        verify_manifest(signed_manifest, public_key=other)


def test_missing_signature_rejected(patched_update_key):
    m = Manifest(
        product="gargoyle-packy", version="2.0.1",
        released_at=datetime.now(timezone.utc).isoformat(),
        requires_support_active=True, upgrade_command="ls",
        changelog_url="https://example.com", min_python_version="3.11",
        notes="", signature="",
    )
    with pytest.raises(ManifestVerificationError):
        verify_manifest(m)


def test_garbage_signature_rejected(patched_update_key, signed_manifest):
    d = signed_manifest.to_dict()
    d["signature"] = "not-base64-!@#$"
    bad = Manifest.from_dict(d)
    with pytest.raises(ManifestVerificationError):
        verify_manifest(bad)


def test_placeholder_public_key_refuses_to_verify(signed_manifest, monkeypatch):
    # Restore the placeholder all-zeros key.
    monkeypatch.setattr(update_keys_mod, "UPDATE_PUBLIC_KEY_RAW", bytes(32))
    with pytest.raises(ManifestVerificationError):
        verify_manifest(signed_manifest)


# --- JSON round trip -----------------------------------------------------

def test_manifest_json_round_trip(signed_manifest):
    blob = signed_manifest.to_signed_json()
    loaded = Manifest.from_json(blob)
    assert loaded.to_dict() == signed_manifest.to_dict()


def test_canonical_format_is_stable():
    m1 = Manifest(
        product="x", version="1.0.0", released_at="2026-01-01T00:00:00Z",
        requires_support_active=True, upgrade_command="a",
        changelog_url="b", min_python_version="3.11",
        notes="z", signature="sig",
    )
    m2 = Manifest(
        product="x", version="1.0.0", released_at="2026-01-01T00:00:00Z",
        requires_support_active=True, upgrade_command="a",
        changelog_url="b", min_python_version="3.11",
        notes="z", signature="sig",
    )
    d1 = m1.to_dict(); d1.pop("signature")
    d2 = m2.to_dict(); d2.pop("signature")
    p1 = json.dumps(d1, separators=(",", ":"), sort_keys=True)
    p2 = json.dumps(d2, separators=(",", ":"), sort_keys=True)
    assert p1 == p2


# --- Checker: end-to-end --------------------------------------------------

def _patch_fetch(monkeypatch, *, blob: str | None = None, status: int = 200, exc: Exception | None = None):
    if exc is not None:
        def fake_urlopen(*a, **kw):
            raise exc
        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        return

    class FakeResp:
        def __init__(self, body: str, status: int):
            self._body = body.encode("utf-8")
            self.status = status
        def read(self) -> bytes:
            return self._body
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def fake_urlopen(req, *a, **kw):
        if blob is None:
            return FakeResp("", status)
        return FakeResp(blob, status)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)


def test_checker_handles_network_failure(patched_update_key, monkeypatch):
    import urllib.error
    _patch_fetch(monkeypatch, exc=urllib.error.URLError("offline"))
    info = check_for_update("2.0.0")
    assert info.available is False
    assert info.signature_ok is False
    assert info.upgrade_command is None
    assert info.error and "offline" in info.error


def test_checker_exposes_upgrade_command_when_signed(patched_update_key, monkeypatch, signed_manifest):
    _patch_fetch(monkeypatch, blob=signed_manifest.to_signed_json())
    info = check_for_update("2.0.0")
    assert info.signature_ok is True
    assert info.upgrade_command == "git pull && pip install -r gargoyle-packy/requirements.txt"
    assert info.latest_version == "2.0.1"
    assert info.available is True
    assert info.notes == "New persona tools, lore fixes."
    assert info.error is None


def test_checker_suppresses_upgrade_command_when_unsigned(monkeypatch, signed_manifest):
    # The manifest is signed by a fresh test key, but the embedded
    # UPDATE_PUBLIC_KEY_RAW is still the placeholder, so verification
    # fails. The checker must still parse the manifest but NOT expose
    # the (potentially attacker-controlled) upgrade_command.
    _patch_fetch(monkeypatch, blob=signed_manifest.to_signed_json())
    info = check_for_update("2.0.0")
    assert info.signature_ok is False
    assert info.upgrade_command is None
    assert info.latest_version == "2.0.1"
    assert info.changelog_url is not None


def test_checker_reports_not_available_when_current_is_newer(patched_update_key, monkeypatch, signed_manifest):
    _patch_fetch(monkeypatch, blob=signed_manifest.to_signed_json())
    info = check_for_update("99.0.0")
    assert info.available is False


def test_checker_handles_invalid_manifest_json(patched_update_key, monkeypatch):
    _patch_fetch(monkeypatch, blob="not json at all")
    info = check_for_update("2.0.0")
    assert info.error and "parse" in info.error.lower()
    assert info.signature_ok is False


# --- Operator CLI: tools.release -----------------------------------------

# CWD for the CLI subprocess — must be the project root so the package
# imports resolve.
_CWD = str(Path(__file__).resolve().parent.parent)


def _run_tools_release(*args) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "tools.release", *args]
    return subprocess.run(
        cmd, capture_output=True, text=True, check=False, cwd=_CWD,
    )


def _run_tools_keygen(*args) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "tools.keygen", *args]
    return subprocess.run(
        cmd, capture_output=True, text=True, check=False, cwd=_CWD,
    )


def test_keygen_init_update_creates_key(tmp_path):
    key_path = tmp_path / "update.pem"
    result = _run_tools_keygen(
        "init-update", "--key-path", str(key_path),
    )
    assert result.returncode == 0, result.stderr
    assert key_path.is_file()
    assert "UPDATE_PUBLIC_KEY_RAW" in result.stdout
    assert "bytes = b'" in result.stdout
    assert (key_path.stat().st_mode & 0o077) == 0


def test_keygen_init_update_is_idempotent(tmp_path):
    key_path = tmp_path / "update.pem"
    _run_tools_keygen("init-update", "--key-path", str(key_path))
    pub1 = key_path.read_bytes()
    _run_tools_keygen("init-update", "--key-path", str(key_path))
    pub2 = key_path.read_bytes()
    assert pub1 == pub2


def test_keygen_init_update_force_overwrites(tmp_path):
    key_path = tmp_path / "update.pem"
    _run_tools_keygen("init-update", "--key-path", str(key_path))
    pub1 = key_path.read_bytes()
    _run_tools_keygen(
        "init-update", "--key-path", str(key_path), "--force",
    )
    pub2 = key_path.read_bytes()
    assert pub1 != pub2


def test_release_sign_manifest_then_verify(tmp_path):
    """End-to-end operator flow: generate update key, sign a manifest,
    verify the result. We verify in-process (passing the public key
    directly) since the embedded update/keys.py is the placeholder."""
    from cryptography.hazmat.primitives import serialization
    key_path = tmp_path / "update.pem"
    _run_tools_keygen("init-update", "--key-path", str(key_path))
    priv = serialization.load_pem_private_key(key_path.read_bytes(), password=None)

    manifest_path = tmp_path / "manifest.json"
    r = _run_tools_release(
        "--key-path", str(key_path),
        "sign-manifest",
        "--version", "2.0.1",
        "--upgrade-command", "git pull",
        "--changelog-url", "https://example.com/changelog",
        "--out", str(manifest_path),
    )
    assert r.returncode == 0, r.stderr
    assert manifest_path.is_file()
    data = json.loads(manifest_path.read_text())
    assert data["version"] == "2.0.1"
    assert data["product"] == "gargoyle-packy"
    assert data["signature"]  # non-empty

    manifest = Manifest.from_json(manifest_path.read_text())
    verify_manifest(manifest, public_key=priv.public_key())  # no exception


def test_release_verify_manifest_rejects_tampered(tmp_path):
    key_path = tmp_path / "update.pem"
    _run_tools_keygen("init-update", "--key-path", str(key_path))
    manifest_path = tmp_path / "manifest.json"
    r1 = _run_tools_release(
        "--key-path", str(key_path),
        "sign-manifest", "--version", "2.0.1",
        "--upgrade-command", "git pull",
        "--changelog-url", "https://example.com",
        "--out", str(manifest_path),
    )
    assert r1.returncode == 0, r1.stderr
    data = json.loads(manifest_path.read_text())
    data["version"] = "9.9.9"
    manifest_path.write_text(json.dumps(data))

    r = _run_tools_release("verify-manifest", str(manifest_path))
    assert r.returncode != 0


# --- Customer CLI: python -m update --------------------------------------

def test_update_cli_runs_without_network_error(monkeypatch, patched_update_key, signed_manifest, tmp_path):
    """`python -m update --help` should work even offline."""
    import urllib.error
    _patch_fetch(monkeypatch, blob=signed_manifest.to_signed_json())
    r = subprocess.run(
        [sys.executable, "-m", "update", "--help"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0
    assert "usage: update" in r.stdout or "usage:" in r.stdout


# --- update package re-exports -------------------------------------------

def test_update_keys_module_exposes_attribute():
    assert hasattr(update_keys_mod, "UPDATE_PUBLIC_KEY_RAW")
    assert isinstance(update_keys_mod.UPDATE_PUBLIC_KEY_RAW, (bytes, bytearray))
    assert len(update_keys_mod.UPDATE_PUBLIC_KEY_RAW) == 32
