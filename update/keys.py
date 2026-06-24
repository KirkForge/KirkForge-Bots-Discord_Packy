"""Embedded update-signing public key for Gargoyle Packy.

This is the customer's trust anchor for the update channel. It MUST
match the operator's update private key (see `tools.keygen init-update`).

A separate key from the license-signing key in `license/keys.py`.
A leaked update key would let an attacker sign fake update manifests,
but NOT forge licenses. The inverse is also true.

Loss of the corresponding private key is non-fatal: existing licenses
keep working, but no new releases can be signed. To recover, an
operator with repo write access can cut a new key, sign a manifest,
and ship a one-time-patch release that includes the new public key.
"""

from __future__ import annotations

# 32-byte Ed25519 public key.
# When the operator runs `python -m tools.keygen init-update` the
# corresponding private key is written to disk and the public half
# printed. Paste the public half here.
#
# Placeholder value (all-zeros) until the first real key is generated.
# Tests detect and reject this.
UPDATE_PUBLIC_KEY_RAW = bytes(32)
