"""Embedded public key for license signature verification.

This is the product's copy of the signing public key. Customers use it to
verify a license file's Ed25519 signature offline. The matching private key
lives outside the product (operator's secure storage) and never ships.

Rotation: bumping the key requires re-signing every active license. The
loader accepts the current key only; older keys are rejected.

To regenerate (operator side, NEVER from inside the product):

    python -m tools.keygen --emit-pubkey

That prints the bytes to paste here.
"""

# PLACEHOLDER — generated 2026-06-13 for development. Ed25519 public key,
# 32 bytes, raw (not PEM). Operator MUST generate a fresh keypair via
# `python -m tools.keygen init-update` (or the Packy variant) and paste
# the public key here before shipping commercial builds.
PUBLIC_KEY_RAW: bytes = (
    b'\xc4\xaf\xc0\x14\x15\xef\xf66\x1f\x08\x04\xa1\xce\xf9\x11\xc5'
    b'\xf5\xf6\xb1Q\xca\xa8\x12\xb8"\xfd\xcf\x06\xe0\xbf\x0fh'
)
