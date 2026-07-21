"""Operator CLI: sign a release manifest for Gargoyle Packy.

Usage:
    python -m tools.release sign-manifest \\
        --version 2.0.1 \\
        --upgrade-command "git pull && pip install -r gargoyle-packy/requirements.txt" \\
        --changelog-url https://github.com/KirkForge/KirkForge-Bots/blob/main/gargoyle-packy/CHANGELOG.md \\
        --out releases/gargoyle-packy/manifest.json

The operator's update private key is loaded from the same default
location as the license key, but with the suffix `.update.pem` so
they don't collide. Generate it with:

    python -m tools.keygen init-update
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from update.manifest import (  # noqa: E402
    Manifest,
    sign_manifest,
    write_manifest_to_path,
)

logger = logging.getLogger("tools.release")

DEFAULT_UPDATE_KEY_PATH = (
    Path.home() / ".local" / "share" / "kirkforge" / "packy" / "private_key.update.pem"
)


def _load_update_key(path: Path) -> Ed25519PrivateKey:
    """Read the update private key from disk.

    On-disk format: PKCS8 PEM (matches what `tools.keygen init-update` writes).
    """
    if not path.is_file():
        raise SystemExit(
            f"FATAL: update private key not found at {path}. "
            f"Generate with: python -m tools.keygen init-update"
        )
    try:
        mode = path.stat().st_mode & 0o777
        if mode & 0o077:
            logger.warning(
                "Update private key %s has permissive mode %04o — should be 0600",
                path,
                mode,
            )
    except OSError:
        pass
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit(
            f"FATAL: {path} is not an Ed25519 key. "
            f"Regenerate with: python -m tools.keygen init-update --force"
        )
    return key


def _cmd_sign_manifest(args: argparse.Namespace) -> int:
    key = _load_update_key(
        Path(args.key_path).expanduser() if args.key_path else DEFAULT_UPDATE_KEY_PATH
    )

    now = datetime.now(timezone.utc)
    manifest = Manifest(
        product=args.product,
        version=args.version,
        released_at=now.isoformat(timespec="seconds"),
        requires_support_active=not args.free,
        upgrade_command=args.upgrade_command,
        changelog_url=args.changelog_url,
        min_python_version=args.min_python,
        notes=args.notes or "",
    )
    signed = sign_manifest(manifest, key)

    out = Path(args.out)
    write_manifest_to_path(signed, out)
    print(f"wrote signed manifest to {out}")
    print(f"  version:    {signed.version}")
    print(f"  released:   {signed.released_at}")
    print(f"  product:    {signed.product}")
    return 0


def _cmd_verify_manifest(args: argparse.Namespace) -> int:
    """Sanity check: read a signed manifest, verify the signature against
    the embedded public key, print the result. Useful right after signing
    and as a smoke test before committing the manifest to the repo."""
    from update.manifest import verify_manifest

    path = Path(args.manifest)
    manifest = Manifest.from_json(path.read_text(encoding="utf-8"))
    try:
        verify_manifest(manifest)
        print(f"OK: {path} is signed by the embedded update key.")
    except Exception as exc:
        print(f"FAIL: {path}: {exc}", file=sys.stderr)
        return 1
    print(f"  version:    {manifest.version}")
    print(f"  released:   {manifest.released_at}")
    print(f"  upgrade:    {manifest.upgrade_command}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(
        prog="release",
        description="Sign + verify release manifests for Gargoyle Packy",
    )
    parser.add_argument(
        "--key-path",
        help=f"Path to the update private key (default: {DEFAULT_UPDATE_KEY_PATH})",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sign = sub.add_parser("sign-manifest", help="Sign a release manifest")
    p_sign.add_argument("--version", required=True, help="Version string, e.g. 2.0.1")
    p_sign.add_argument(
        "--upgrade-command",
        required=True,
        help="Shell command customers should run to upgrade (e.g. 'git pull && pip install ...')",
    )
    p_sign.add_argument(
        "--changelog-url",
        required=True,
        help="URL to the changelog for this release",
    )
    p_sign.add_argument(
        "--min-python", default="3.11", help="Minimum Python version (default: 3.11)"
    )
    p_sign.add_argument(
        "--notes",
        default="",
        help="Optional release notes (shown to customers)",
    )
    p_sign.add_argument(
        "--product",
        default="gargoyle-packy",
        help="Product ID (default: gargoyle-packy)",
    )
    p_sign.add_argument(
        "--free",
        action="store_true",
        help="This release does NOT require an active support contract (default: required)",
    )
    p_sign.add_argument(
        "--out",
        required=True,
        help="Output path for the signed manifest.json",
    )
    p_sign.set_defaults(func=_cmd_sign_manifest)

    p_verify = sub.add_parser("verify-manifest", help="Verify a manifest on disk")
    p_verify.add_argument("manifest", help="Path to manifest.json")
    p_verify.set_defaults(func=_cmd_verify_manifest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
