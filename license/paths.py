"""Where the loader looks for the license file.

Search order, first hit wins:

    1. $PACKY_LICENSE_PATH       (operator override, e.g. CI, container)
    2. ./license.json             (current working directory)
    3. $XDG_CONFIG_HOME/kirkforge/packy/license.json
    4. ~/.config/kirkforge/packy/license.json   (default XDG home)
    5. /etc/kirkforge/packy/license.json         (system-wide)

The first one that exists is read. If none exist, `LicenseNotFoundError`
is raised and the boot gate refuses to start.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_LICENSE_PATH = "PACKY_LICENSE_PATH"
_FILE_BASENAME = "license.json"


def search_paths() -> list[Path]:
    """Return the candidate paths in priority order, with existence flag."""
    candidates: list[Path] = []

    env = os.environ.get(ENV_LICENSE_PATH, "").strip()
    if env:
        candidates.append(Path(env))

    candidates.append(Path.cwd() / _FILE_BASENAME)

    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    user_cfg = Path(xdg) if xdg else Path.home() / ".config"
    candidates.append(user_cfg / "kirkforge" / "packy" / _FILE_BASENAME)

    candidates.append(Path("/etc/kirkforge/packy") / _FILE_BASENAME)

    return candidates


def find_license_file() -> Path:
    """Return the first existing candidate path.

    Raises LicenseNotFoundError with a helpful message if none exist.
    """
    from .errors import LicenseNotFoundError  # local import: avoid cycle at module load

    tried: list[Path] = []
    for candidate in search_paths():
        tried.append(candidate)
        if candidate.is_file():
            return candidate

    pretty = "\n  ".join(str(p) for p in tried)
    raise LicenseNotFoundError(
        "No Gargoyle Packy license found. Searched:\n  "
        + pretty
        + "\n\nTo obtain a license, visit https://kirkforge.com/packy/pricing.\n"
        "After purchase, place your license file at one of the above paths, or\n"
        f"set the {ENV_LICENSE_PATH} environment variable to point at it."
    )
