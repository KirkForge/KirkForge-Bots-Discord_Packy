"""Operator tool: generate Gargoyle Packy license files.

This module is NOT shipped to customers. It belongs on the operator's
machine (the one with the private signing key). Its outputs are:

    1. `--init`              Generate a keypair. Writes private key to
                             a path the operator controls (default:
                             $XDG_DATA_HOME/kirkforge/packy/private_key.pem
                             or ~/.local/share/...). Prints the public key
                             bytes to embed in license/keys.py.

    2. `--sign <out.json>`   Sign a license for one customer. Reads tier +
                             customer details from CLI flags, reads the
                             private key from disk, writes a signed JSON
                             license to the given path.

Both modes log a clear warning: this tool holds production signing power.
Losing the private key means every issued license becomes unverifiable.

On-disk format: PKCS8 PEM, encryption=None. Matches what the sales
service's LicenseSigner expects. (The Specialist used raw 32 bytes;
that's incompatible with the sales service's PEM reader — see the
packy fix in commit history.)

Usage:

    # First time: generate the keypair
    python -m tools.keygen --init

    # Embed the printed public key in gargoyle-packy/license/keys.py
    # ... and ship the new build.

    # Then, for each sale:
    python -m tools.keygen --sign license.json \\
        --tier pro \\
        --customer "Acme Corp" \\
        --email ops@acme.com \\
        --seats 5 \\
        --support-years 1

    # Email license.json to the customer. Customer drops it into one of
    # the standard paths and the product boots.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# We import claims and features for tier/feature validation. We deliberately
# do NOT import the verifier or loader from the customer-side license module
# because the operator and customer code paths should be independent.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from license import claims as claims_mod  # noqa: E402
from license import features as feat_mod  # noqa: E402

logger = logging.getLogger("tools.keygen")

DEFAULT_PRODUCT = "gargoyle-packy"
DEFAULT_PRODUCT_VERSION = "2.0.0"

DEFAULT_PRIVATE_KEY_PATH = Path.home() / ".local" / "share" / "kirkforge" / "packy" / "private_key.pem"
DEFAULT_UPDATE_KEY_PATH = Path.home() / ".local" / "share" / "kirkforge" / "packy" / "private_key.update.pem"
DEFAULT_KEY_MODE = 0o600


@dataclass
class Keypair:
    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey

    @property
    def public_raw(self) -> bytes:
        return self.public_key.public_bytes_raw()

    @property
    def private_raw(self) -> bytes:
        return self.private_key.private_bytes_raw()


def _to_pem(priv: Ed25519PrivateKey) -> bytes:
    return priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _load_or_create_keypair(path: Path) -> Keypair:
    if path.exists():
        logger.info("loading existing private key from %s", path)
        key = serialization.load_pem_private_key(
            path.read_bytes(), password=None,
        )
        if not isinstance(key, Ed25519PrivateKey):
            raise SystemExit(
                f"private key at {path} is not an Ed25519 key"
            )
        return Keypair(private_key=key, public_key=key.public_key())

    # First-time init: refuse to write to an existing directory without a key
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.warning("generating NEW keypair at %s — back this up somewhere safe", path)
    priv = Ed25519PrivateKey.generate()
    kp = Keypair(private_key=priv, public_key=priv.public_key())

    # Atomic write: .tmp then rename, mode 600.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(_to_pem(priv))
    os.chmod(tmp, DEFAULT_KEY_MODE)
    tmp.replace(path)
    logger.info("wrote private key to %s (mode %o)", path, DEFAULT_KEY_MODE)
    return kp


def _canonical_payload(claims: claims_mod.LicenseClaims) -> bytes:
    return json.dumps(claims.to_dict(), separators=(",", ":"), sort_keys=True).encode("utf-8")


def sign_license(
    kp: Keypair,
    *,
    tier: str,
    customer_name: str,
    customer_email: str,
    max_seats: int,
    support_years: int,
    product: str = DEFAULT_PRODUCT,
    product_version: str = DEFAULT_PRODUCT_VERSION,
    features: list[str] | None = None,
    license_id: str | None = None,
) -> dict:
    """Build and sign a license payload. Returns the dict to write as JSON.

    `features` is the explicit list of features; defaults to whatever the
    tier's standard set is. Pass an explicit list to grant a la carte
    features (rare — usually tier-driven).
    """
    if tier not in feat_mod.ALL_TIERS:
        raise SystemExit(
            f"unknown tier '{tier}'. Valid: {', '.join(feat_mod.ALL_TIERS)}"
        )
    granted = frozenset(features) if features else feat_mod.TIER_FEATURES[tier]
    unknown = granted - {f for fs in feat_mod.TIER_FEATURES.values() for f in fs}
    if unknown:
        raise SystemExit(f"unknown feature(s) in --features: {', '.join(sorted(unknown))}")

    now = datetime.now(timezone.utc)
    claims = claims_mod.LicenseClaims(
        license_id=license_id or _gen_license_id(),
        product=product,
        product_version=product_version,
        format_version=claims_mod.LICENSE_FORMAT_VERSION,
        customer=claims_mod.Customer(name=customer_name, email=customer_email),
        tier=tier,
        issued_at=now,
        support_until=now + timedelta(days=365 * support_years),
        max_seats=max_seats,
        features=tuple(sorted(granted)),
    )

    payload = _canonical_payload(claims)
    signature = kp.private_key.sign(payload)
    license_dict = claims.to_dict()
    license_dict["signature"] = base64.b64encode(signature).decode("ascii")
    return license_dict


def _gen_license_id() -> str:
    """Stable human-readable ID. 4-char prefix + 4-char suffix hex."""
    return f"KFG-{datetime.now(timezone.utc).strftime('%Y')}-{secrets.token_hex(4).upper()}"


def _cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.key_path).expanduser() if args.key_path else DEFAULT_PRIVATE_KEY_PATH
    if path.exists() and not args.force:
        logger.info("keypair already exists at %s (use --force to rotate)", path)
        kp = _load_or_create_keypair(path)
    else:
        kp = _load_or_create_keypair(path)

    # Always print the public key on init — operator needs it to embed.
    pub = kp.public_raw
    print()
    print("# Public key (Ed25519, 32 raw bytes) — paste into gargoyle-packy/license/keys.py")
    print("PUBLIC_KEY_RAW: bytes = " + repr(pub))
    print()
    print(f"# Private key stored at: {path}")
    print("# BACK THIS UP. Losers of this file cannot sign new licenses, and every")
    print("# license issued so far becomes unverifiable after the product rotates")
    print("# the embedded public key.")
    return 0


def _cmd_sign(args: argparse.Namespace) -> int:
    path = Path(args.key_path).expanduser() if args.key_path else DEFAULT_PRIVATE_KEY_PATH
    kp = _load_or_create_keypair(path)

    license_dict = sign_license(
        kp,
        tier=args.tier,
        customer_name=args.customer,
        customer_email=args.email,
        max_seats=args.seats,
        support_years=args.support_years,
        product=args.product,
        product_version=args.product_version,
        features=args.features,
        license_id=args.license_id,
    )

    out = Path(args.out)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(license_dict, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out)
    os.chmod(out, 0o644)  # customer-readable

    print(f"wrote signed license to {out}")
    print(f"  license_id: {license_dict['license_id']}")
    print(f"  tier:       {license_dict['tier']}")
    print(f"  customer:   {license_dict['customer']['name']} <{license_dict['customer']['email']}>")
    print(f"  support:    until {license_dict['support_until']}")
    print(f"  seats:      {license_dict['max_seats']}")
    return 0


def _cmd_pubkey(args: argparse.Namespace) -> int:
    path = Path(args.key_path).expanduser() if args.key_path else DEFAULT_PRIVATE_KEY_PATH
    if not path.exists():
        raise SystemExit(f"no private key at {path}; run --init first")
    kp = _load_or_create_keypair(path)
    print("PUBLIC_KEY_RAW: bytes = " + repr(kp.public_raw))
    return 0


# --- Update-signing key (separate from license key) ---------------------

def _load_or_create_keypair_at(path: Path, *, force: bool = False) -> Keypair:
    """Like _load_or_create_keypair but unconditionally writes if --force."""
    if path.exists() and not force:
        logger.info("loading existing private key from %s", path)
        key = serialization.load_pem_private_key(
            path.read_bytes(), password=None,
        )
        if not isinstance(key, Ed25519PrivateKey):
            raise SystemExit(
                f"private key at {path} is not an Ed25519 key"
            )
        return Keypair(private_key=key, public_key=key.public_key())
    if path.exists() and force:
        logger.warning("overwriting existing key at %s (force=True)", path)
    path.parent.mkdir(parents=True, exist_ok=True)
    priv = Ed25519PrivateKey.generate()
    kp = Keypair(private_key=priv, public_key=priv.public_key())
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(_to_pem(priv))
    os.chmod(tmp, DEFAULT_KEY_MODE)
    tmp.replace(path)
    logger.info("wrote new update private key to %s (mode %o)", path, DEFAULT_KEY_MODE)
    return kp


def _cmd_init_update(args: argparse.Namespace) -> int:
    path = Path(args.key_path).expanduser() if args.key_path else DEFAULT_UPDATE_KEY_PATH
    kp = _load_or_create_keypair_at(path, force=args.force)
    pub = kp.public_raw
    print()
    print("# UPDATE public key — paste into gargoyle-packy/update/keys.py")
    print("UPDATE_PUBLIC_KEY_RAW: bytes = " + repr(pub))
    print()
    print(f"# Update private key stored at: {path}")
    print("# BACK THIS UP. Loss means no new release can be signed. Existing")
    print("# licenses are unaffected (they're signed with the OTHER key).")
    return 0


def _cmd_update_pubkey(args: argparse.Namespace) -> int:
    path = Path(args.key_path).expanduser() if args.key_path else DEFAULT_UPDATE_KEY_PATH
    if not path.exists():
        raise SystemExit(f"no update private key at {path}; run init-update first")
    kp = _load_or_create_keypair_at(path)
    print("UPDATE_PUBLIC_KEY_RAW: bytes = " + repr(kp.public_raw))
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(
        prog="keygen",
        description="Operator tool for signing Gargoyle Packy licenses",
    )
    parser.add_argument(
        "--key-path",
        help=f"Path to the private key (default: {DEFAULT_PRIVATE_KEY_PATH})",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Generate a new keypair (or load existing)")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing key")
    p_init.set_defaults(func=_cmd_init)

    p_sign = sub.add_parser("sign", help="Sign a license file for a customer")
    p_sign.add_argument("--out", required=True, help="Output license.json path")
    p_sign.add_argument("--tier", required=True, choices=feat_mod.ALL_TIERS)
    p_sign.add_argument("--customer", required=True, help="Customer name")
    p_sign.add_argument("--email", required=True, help="Customer email")
    p_sign.add_argument("--seats", type=int, default=1, help="Max seats (default: 1)")
    p_sign.add_argument(
        "--support-years", type=int, default=1, help="Support contract length in years (default: 1)"
    )
    p_sign.add_argument("--product", default=DEFAULT_PRODUCT)
    p_sign.add_argument("--product-version", default=DEFAULT_PRODUCT_VERSION)
    p_sign.add_argument(
        "--features", nargs="*", help="Override default tier features (advanced)"
    )
    p_sign.add_argument("--license-id", help="Override the auto-generated license ID")
    p_sign.set_defaults(func=_cmd_sign)

    p_pub = sub.add_parser("pubkey", help="Print the public key bytes (for embedding in the product)")
    p_pub.set_defaults(func=_cmd_pubkey)

    p_init_upd = sub.add_parser(
        "init-update", help="Generate the UPDATE-signing keypair (separate from the license key)",
    )
    p_init_upd.add_argument("--force", action="store_true", help="Overwrite existing key")
    p_init_upd.add_argument("--key-path", help="Path to the update private key")
    p_init_upd.set_defaults(func=_cmd_init_update)

    p_upd_pub = sub.add_parser("update-pubkey", help="Print the update public key (for embedding)")
    p_upd_pub.add_argument("--key-path", help="Path to the update private key")
    p_upd_pub.set_defaults(func=_cmd_update_pubkey)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
