# core/SNARK/__init__.py — make SNARK importable from core
# This file can be empty or export convenience names.
# Defensive imports to avoid breaking startup

try:
    from .packy_snark import *  # noqa: F403
except ImportError:
    pass

try:
    from .packy_actions import *  # noqa: F403
except ImportError:
    pass

try:
    from .packy_teaching import *  # noqa: F403
except ImportError:
    pass
