"""Customer CLI: `python -m update`.

Usage:
    python -m update              # check + report
    python -m update --apply      # check + run the upgrade command
    python -m update --manifest-url <url>   # override the default manifest URL

We deliberately do NOT auto-update. AGENTS.md forbids it. The customer
must run --apply explicitly, and we always print the upgrade command
and the URL it would shell out to (well, it's a string, not a URL, but
the point is they have to read it before pressing Y).
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Make the project root importable when invoked as `python -m update`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from update.checker import check_for_update  # noqa: E402
from update.manifest import DEFAULT_MANIFEST_URL  # noqa: E402

logger = logging.getLogger("update")


def _current_version() -> str:
    """Read the product version from pyproject.toml (best-effort)."""
    import re

    pyproject = _PROJECT_ROOT / "pyproject.toml"
    if not pyproject.is_file():
        return "0.0.0"
    text = pyproject.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else "0.0.0"


def _print_check(check) -> None:
    print(f"  current:       {check.current_version}")
    print(f"  latest:        {check.latest_version or '(unknown)'}")
    print(f"  available:     {'yes' if check.available else 'no'}")
    print(f"  signature_ok:  {'yes' if check.signature_ok else 'NO'}")
    print(f"  published_at:  {check.published_at or '(unknown)'}")
    if check.changelog_url:
        print(f"  changelog:     {check.changelog_url}")
    if check.release_notes:
        print()
        print("  Release notes:")
        for line in check.release_notes.splitlines():
            print(f"    {line}")
    if check.error:
        print()
        print(f"  WARNING: {check.error}")
    if check.requires_support_active:
        print()
        print("  This release requires an active support contract.")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(
        prog="update",
        description="Check for updates to Gargoyle Packy. Manual only — no auto-update.",
    )
    parser.add_argument(
        "--manifest-url",
        default=DEFAULT_MANIFEST_URL,
        help="Override the manifest URL (default: %(default)s)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="After a successful check, run the upgrade command. Prompts for confirmation.",
    )
    args = parser.parse_args(argv)

    current = _current_version()
    print(f"Checking for updates to Gargoyle Packy (current: {current})…")
    print(f"  manifest: {args.manifest_url}")
    print()
    check = check_for_update(current, manifest_url=args.manifest_url)

    _print_check(check)

    if not check.signature_ok:
        print()
        print("Refusing to suggest an upgrade: the manifest is not signed by a key we trust.")
        return 2

    if not check.available:
        print()
        print("Already on the latest version. Nothing to do.")
        return 0

    print()
    print("To upgrade, the manifest says to run:")
    print(f"    {check.upgrade_command}")

    if not args.apply:
        print()
        print("Re-run with --apply to run this command (you will be asked to confirm).")
        return 0

    # --apply
    print()
    print("This will run the above command via `sh -c`. Type 'yes' to continue: ", end="")
    try:
        answer = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\naborted")
        return 1
    if answer != "yes":
        print("aborted")
        return 1

    print()
    print(f"$ {check.upgrade_command}")
    result = subprocess.run(check.upgrade_command, shell=True, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
