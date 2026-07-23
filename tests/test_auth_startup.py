"""Auth-required-at-startup tests for packy_endpoint.py.

Verifies that:
- Missing PACKY_API_SECRET causes SystemExit(1) when PACKY_DEV_LICENSE is not set.
- Setting PACKY_DEV_LICENSE=1 allows startup without PACKY_API_SECRET.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_auth_required_on_startup_no_secret_no_dev_license(monkeypatch):
    """Server must refuse to start when PACKY_API_SECRET is empty and
    PACKY_DEV_LICENSE is not set."""
    monkeypatch.delenv("PACKY_API_SECRET", raising=False)
    monkeypatch.delenv("PACKY_DEV_LICENSE", raising=False)

    if "src.orchestration.packy_endpoint" in sys.modules:
        del sys.modules["src.orchestration.packy_endpoint"]

    with pytest.raises(SystemExit) as exc_info:
        import src.orchestration.packy_endpoint as _mod  # noqa: F401

    assert exc_info.value.code == 1


def test_auth_bypass_in_dev_mode(monkeypatch):
    """Setting PACKY_DEV_LICENSE=1 allows startup without PACKY_API_SECRET."""
    monkeypatch.delenv("PACKY_API_SECRET", raising=False)
    monkeypatch.setenv("PACKY_DEV_LICENSE", "1")

    # Also need a license for full startup, but we're just testing the
    # auth gate — patch boot_license so the import doesn't exit early.
    if "src.orchestration.packy_endpoint" in sys.modules:
        del sys.modules["src.orchestration.packy_endpoint"]

    with patch("src.orchestration.packy_endpoint.boot_license"):
        import src.orchestration.packy_endpoint as mod

    assert mod._bypass_auth is True
    assert mod.API_SECRET == ""


def test_auth_enabled_when_secret_set(monkeypatch):
    """When PACKY_API_SECRET is set, auth is enabled and _bypass_auth is False."""
    monkeypatch.setenv("PACKY_API_SECRET", "test-secret-value-that-is-long-enough")
    monkeypatch.delenv("PACKY_DEV_LICENSE", raising=False)

    if "src.orchestration.packy_endpoint" in sys.modules:
        del sys.modules["src.orchestration.packy_endpoint"]

    with patch("src.orchestration.packy_endpoint.boot_license"):
        import src.orchestration.packy_endpoint as mod

    assert mod._bypass_auth is False
    assert mod.API_SECRET == "test-secret-value-that-is-long-enough"


def test_auth_check_header_with_secret(monkeypatch):
    """_check_auth_header validates bearer tokens using timing-safe comparison."""
    monkeypatch.setenv("PACKY_API_SECRET", "my-secret-token")
    monkeypatch.delenv("PACKY_DEV_LICENSE", raising=False)

    if "src.orchestration.packy_endpoint" in sys.modules:
        del sys.modules["src.orchestration.packy_endpoint"]

    with patch("src.orchestration.packy_endpoint.boot_license"):
        import src.orchestration.packy_endpoint as mod

    assert mod._check_auth_header({"authorization": "Bearer my-secret-token"}) is True
    assert mod._check_auth_header({"authorization": "Bearer wrong-token"}) is False
    assert mod._check_auth_header({}) is False
