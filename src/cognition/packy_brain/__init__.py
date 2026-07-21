"""PackyBrain v2.05 — central brain integration module.

Public API (preserved from the original packy_brain.py):
    class PackyBrain
    def get_packy(force_new: bool = False) -> PackyBrain

The original 807-line single class has been split into one mixin per concern
(__init__, _state, _triggers, _snark, _personality, _tts, _memory, _scripts,
_teach, _cognition, _summary). This __init__.py composes the mixins via
multiple inheritance, and the MRO ensures PackyInitMixin.__init__ is the one
that runs.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path
from typing import Optional

_CORE_DIR = Path(__file__).resolve().parent
if str(_CORE_DIR) not in _sys.path:
    _sys.path.insert(0, str(_CORE_DIR))

from ._cognition import PackyCognitionMixin
from ._init import PackyInitMixin
from ._memory import PackyMemoryMixin
from ._personality import PackyPersonalityMixin
from ._scripts import PackyScriptsMixin
from ._setup import logger as _setup_logger
from ._snark import PackySnarkMixin
from ._state import PackyStateMixin
from ._summary import PackySummaryMixin
from ._teach import PackyTeachMixin
from ._triggers import PackyTriggersMixin
from ._tts import PackyTtsMixin


class PackyBrain(
    PackyInitMixin,
    PackyStateMixin,
    PackyTriggersMixin,
    PackySnarkMixin,
    PackyPersonalityMixin,
    PackyTtsMixin,
    PackyMemoryMixin,
    PackyScriptsMixin,
    PackyTeachMixin,
    PackyCognitionMixin,
    PackySummaryMixin,
):
    VERSION = PackyInitMixin.VERSION


_PACKY_SINGLETON: Optional[PackyBrain] = None


def get_packy(force_new: bool = False) -> PackyBrain:
    global _PACKY_SINGLETON
    if _PACKY_SINGLETON is None or force_new:
        _PACKY_SINGLETON = PackyBrain(load_on_init=True)
        _setup_logger.info("PackyBrain singleton created")
    return _PACKY_SINGLETON


__all__ = ["PackyBrain", "get_packy"]
