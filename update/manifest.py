"""Release manifest — signed, signed, signed.

A release manifest is a JSON file the operator publishes when shipping
a new version of Gargoyle Packy. It says:
  - which version is current
  - when it shipped
  - whether the customer's support contract needs to be active to install
  - the command to run to upgrade (a git pull, typically)
  - where the changelog lives
  - minimum Python version

The manifest is signed with the operator's UPDATE key. The customer
fetches it, verifies the signature against `update.keys.UPDATE_PUBLIC_KEY_RAW`,
and only then trusts the contents.

Canonical signing format: same pattern as `license.claims` —
  payload = json.dumps(claims_dict, separators=(",", ":"), sort_keys=True)
  signature = ed25519.sign(payload)
The `signature` field is the base64 of the signature and is NOT
included in the signed bytes.
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from update import keys as _keys

logger = logging.getLogger(__name__)


@dataclass
class Manifest:
    product: str
    version: str
    released_at: str
    requires_support_active: bool
    upgrade_command: str
    changelog_url: str
    min_python_version: str
    notes: str = ""
    signature: str = ""

    # --- Canonical (de)serialization --------------------------------

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Manifest":
        # Accept either signed or unsigned; the `signature` field is
        # optional at construction time, required for verification.
        return cls(
            product=d["product"],
            version=d["version"],
            released_at=d["released_at"],
            requires_support_active=bool(d["requires_support_active"]),
            upgrade_command=d["upgrade_command"],
            changelog_url=d["changelog_url"],
            min_python_version=d["min_python_version"],
            notes=d.get("notes", ""),
            signature=d.get("signature", ""),
        )

    def to_signed_json(self) -> str:
        """JSON ready to write to disk. The signature is included."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, blob: str) -> "Manifest":
        return cls.from_dict(json.loads(blob))


# --- Signing (operator side) ---------------------------------------------

def sign_manifest(
    manifest: Manifest,
    private_key,
) -> Manifest:
    """Return a NEW manifest with the signature filled in.

    Does not mutate the input. The signing format is:
        payload = json.dumps(claims_dict, separators=(",", ":"), sort_keys=True)
    where `claims_dict` is the manifest dict WITHOUT the `signature` field.
    """
    d = manifest.to_dict()
    d.pop("signature", None)
    payload = json.dumps(d, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = private_key.sign(payload)
    return Manifest(
        **{**d, "signature": base64.b64encode(sig).decode("ascii")}
    )


# --- Verification (customer side) ---------------------------------------

class ManifestVerificationError(Exception):
    """Raised when a manifest cannot be trusted.

    Callers MUST NOT act on a manifest that raises this. Reasons include
    missing signature, signature mismatch, or wrong public key.
    """


def verify_manifest(manifest: Manifest, *, public_key=None) -> None:
    """Raise ManifestVerificationError if the signature is invalid.

    The `public_key` argument is for tests; production uses the
    embedded `update.keys.UPDATE_PUBLIC_KEY_RAW`.
    """
    pk_raw = bytes(public_key.public_bytes_raw() if public_key is not None else _keys.UPDATE_PUBLIC_KEY_RAW)
    if not pk_raw or pk_raw == bytes(32):
        raise ManifestVerificationError(
            "update public key is unset (still the placeholder); refuse to verify"
        )
    if not manifest.signature:
        raise ManifestVerificationError("manifest has no signature")
    try:
        sig = base64.b64decode(manifest.signature, validate=True)
    except Exception as exc:
        raise ManifestVerificationError(f"signature is not valid base64: {exc}") from exc
    # Reconstruct the signed bytes the same way sign_manifest did.
    d = manifest.to_dict()
    d.pop("signature", None)
    payload = json.dumps(d, separators=(",", ":"), sort_keys=True).encode("utf-8")
    try:
        Ed25519PublicKey.from_public_bytes(pk_raw).verify(sig, payload)
    except InvalidSignature as exc:
        raise ManifestVerificationError("signature does not match claims") from exc


# --- Fetching (customer side) --------------------------------------------

DEFAULT_MANIFEST_URL = (
    "https://raw.githubusercontent.com/KirkForge/KirkForge-Bots/main/"
    "releases/gargoyle-packy/manifest.json"
)
TIMEOUT_SECONDS = 5.0
USER_AGENT = "kirkforge-packy-updater/0.1"


def fetch_manifest(url: str = DEFAULT_MANIFEST_URL, *, timeout: float = TIMEOUT_SECONDS) -> str:
    """Fetch the raw manifest JSON. Raises on network failure."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise ManifestVerificationError(
                f"manifest fetch returned HTTP {resp.status}"
            )
        return resp.read().decode("utf-8")


def load_manifest_from_path(path: Path) -> Manifest:
    """Read a manifest from disk (used by both sides in dev)."""
    return Manifest.from_json(path.read_text(encoding="utf-8"))


def write_manifest_to_path(manifest: Manifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.to_signed_json(), encoding="utf-8")
