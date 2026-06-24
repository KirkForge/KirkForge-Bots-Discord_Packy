"""Update channel for Gargoyle Packy.

This package is the customer-facing side of the update mechanism.
The operator side lives in `tools.release`.

Design:
  1. Operator signs a release manifest with an Ed25519 update key
     (separate from the license key, so a leaked update key can't
     be used to forge licenses).
  2. The manifest is hosted at a known URL (default: a file committed
     to the KirkForge-Bots GitHub repo).
  3. The Packy cognition service fetches the manifest, verifies
     the signature against the embedded public key, and reports.
  4. The customer runs `python -m update` to check + apply.

This is a MANUAL update channel. Auto-update is forbidden per AGENTS.md.
"""
