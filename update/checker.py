"""Update checker — fetch, verify, report.

This is the customer-facing side of the update channel. The Packy cognition
service's `/admin/update` endpoint and the `python -m update` CLI both
go through here.

Network behavior: a single HTTPS GET to the manifest URL, with a short
timeout. We never block on it — failures are returned as a structured
`UpdateCheck` with an `error` field so callers can show a clean line.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from update.manifest import (
    DEFAULT_MANIFEST_URL,
    Manifest,
    ManifestVerificationError,
    verify_manifest,
)

logger = logging.getLogger(__name__)


@dataclass
class UpdateCheck:
    """Result of a single update check. Always safe to return to a UI:
    a verification failure is just `signature_ok=False`, not an exception."""

    current_version: str
    latest_version: str | None
    available: bool
    signature_ok: bool
    upgrade_command: str | None  # only set when signature_ok=True
    changelog_url: str | None
    release_notes: str | None
    notes: str | None  # alias for release_notes (operator-facing)
    requires_support_active: bool
    published_at: str | None
    checked_at: str
    manifest_url: str
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_version(tag: str) -> tuple[int, ...]:
    s = tag.lstrip("vV").strip()
    parts: list[int] = []
    for chunk in s.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            return (0,)
    return tuple(parts) if parts else (0,)


def _new_check(current_version: str, manifest_url: str, error: str | None = None) -> UpdateCheck:
    """Empty success-shape check, used as the base for error returns."""
    return UpdateCheck(
        current_version=current_version,
        latest_version=None,
        available=False,
        signature_ok=False,
        upgrade_command=None,
        changelog_url=None,
        release_notes=None,
        notes=None,
        requires_support_active=False,
        published_at=None,
        checked_at=datetime.now(timezone.utc).isoformat(),
        manifest_url=manifest_url,
        error=error,
    )


def check_for_update(
    current_version: str,
    *,
    manifest_url: str = DEFAULT_MANIFEST_URL,
    timeout: float = 5.0,
) -> UpdateCheck:
    """Fetch + verify the manifest. Never raises — returns a structured result."""
    now = datetime.now(timezone.utc).isoformat()

    # 1. Fetch
    try:
        req = urllib.request.Request(
            manifest_url,
            headers={"User-Agent": "kirkforge-packy-updater/0.1", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return _new_check(
                    current_version,
                    manifest_url,
                    error=f"manifest fetch returned HTTP {resp.status}",
                )
            blob = resp.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        return _new_check(
            current_version,
            manifest_url,
            error=f"fetch failed: {exc}",
        )

    # 2. Parse
    try:
        manifest = Manifest.from_json(blob)
    except Exception as exc:
        return _new_check(
            current_version,
            manifest_url,
            error=f"manifest parse failed: {exc}",
        )

    # 3. Verify signature
    try:
        verify_manifest(manifest)
        signature_ok = True
        verify_error: str | None = None
    except ManifestVerificationError as exc:
        # Surface the unverified data but DO NOT expose upgrade_command —
        # that field would let an attacker ship arbitrary shell.
        signature_ok = False
        verify_error = f"signature verification failed: {exc}"

    return UpdateCheck(
        current_version=current_version,
        latest_version=manifest.version,
        available=_parse_version(manifest.version) > _parse_version(current_version),
        signature_ok=signature_ok,
        upgrade_command=manifest.upgrade_command if signature_ok else None,
        changelog_url=manifest.changelog_url,
        release_notes=manifest.notes,
        notes=manifest.notes,
        requires_support_active=manifest.requires_support_active,
        published_at=manifest.released_at,
        checked_at=now,
        manifest_url=manifest_url,
        error=verify_error,
    )
