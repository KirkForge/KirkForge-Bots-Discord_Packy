"""Ed25519 signature verification for license files.

The signed payload is the JSON of every field except `signature`,
serialized canonically (sorted keys, no whitespace). The 32-byte raw
Ed25519 public key is embedded in `license/keys.py`.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from . import keys as _keys
from .errors import LicenseFormatError, LicenseSignatureError

logger = logging.getLogger(__name__)

# SHA-512 over the canonical payload; Ed25519 signs the message directly,
# but the canonicalization step is what makes verification deterministic.
_CANONICAL_SEPARATORS = (",", ":")


def _canonical_payload(claims_dict: dict[str, Any]) -> bytes:
    """Re-serialize the claims portion (everything but `signature`) deterministically.

    `sort_keys=True` plus fixed separators gives a stable byte representation
    regardless of how the license was originally written.
    """
    payload = {k: v for k, v in claims_dict.items() if k != "signature"}
    return json.dumps(payload, separators=_CANONICAL_SEPARATORS, sort_keys=True).encode("utf-8")


def verify_signature(license_dict: dict[str, Any]) -> None:
    """Raise if the embedded signature doesn't match the embedded public key.

    Idempotent and side-effect-free; the loader calls this once and discards
    the raw dict in favor of the typed `LicenseClaims`.
    """
    if not _keys.PUBLIC_KEY_RAW or len(_keys.PUBLIC_KEY_RAW) != 32:
        raise LicenseSignatureError(
            "Product is missing its embedded license public key. "
            "This indicates a broken build — reinstall from a clean source."
        )

    sig_b64 = license_dict.get("signature")
    if not isinstance(sig_b64, str):
        raise LicenseFormatError("license file missing 'signature' field")

    try:
        signature = base64.b64decode(sig_b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise LicenseFormatError(f"signature is not valid base64: {exc}") from exc

    if len(signature) != 64:
        raise LicenseFormatError(f"signature must be 64 bytes (Ed25519), got {len(signature)}")

    message = _canonical_payload(license_dict)
    pubkey = Ed25519PublicKey.from_public_bytes(_keys.PUBLIC_KEY_RAW)

    try:
        pubkey.verify(signature, message)
    except InvalidSignature as exc:
        raise LicenseSignatureError(
            "License signature failed verification. The file is either forged, "
            "tampered with, or signed by a key the product no longer trusts. "
            "Re-download your license from kirkforge.com/account."
        ) from exc

    logger.debug("license signature verified (%d bytes payload)", len(message))
