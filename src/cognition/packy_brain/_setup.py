"""PackyBrain v2.05 — module setup, defensive imports, fallback utilities.

Extracted from the original packy_brain.py (lines 1-106). This file is the
*first* module loaded by the subpackage's __init__.py; it provides:
  - the package logger
  - the _try_import helper for defensive optional imports
  - the _snark_modules dict of optional module handles
  - the PackyCogEngine binding (if packy_cog_engine is importable)
  - the _default_get_snark_lines / _default_generate_script fallbacks
"""

from __future__ import annotations

import logging
import random
import sys as _sys
from pathlib import Path
from typing import List

logger = logging.getLogger("packy.brain")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

CORE_DIR = Path(__file__).resolve().parent
ROOT_DIR = CORE_DIR.parent
PERSISTENT_DIR = ROOT_DIR / "persistent"

if str(CORE_DIR) not in _sys.path:
    _sys.path.insert(0, str(CORE_DIR))


def _try_import(module_name: str):
    try:
        module = __import__(module_name, fromlist=["*"])
        logger.debug("Imported %s", module_name)
        return module
    except Exception as e:
        logger.debug("Could not import %s: %s", module_name, e)
        return None


_snark_modules = {
    "snark_engine": _try_import("packy_snark"),
    "snark": _try_import("packy_snark"),
    "teaching": _try_import("generators.packy_teaching"),
    "lore_writer": _try_import("packy_lore_writer"),
    "bash_gen": _try_import("generators.bash_script_generator"),
    "python_gen": _try_import("generators.python_script_generator"),
    "pwsh_gen": _try_import("generators.powershell_script_generator"),
    "actions": _try_import("packy_actions"),
    "memory_tools": _try_import("packy_memory_tools"),
    "persona_tools": _try_import("packy_persona_tools"),
    "behavior_profiles": _try_import("packy_behavior_profiles"),
}

_persist_module = _try_import("persistent.persistant_loader")
_packy_memory_module = _try_import("persistent.packy_memory")
_memory_adapter_module = _try_import("persistent.memory_adapter")
_persona_module = _try_import("packy_persona")
_cog_module = _try_import("packy_cog_engine")

PackyCogEngine = None
if _cog_module and hasattr(_cog_module, "PackyCogEngine"):
    try:
        PackyCogEngine = getattr(_cog_module, "PackyCogEngine")
    except Exception:
        PackyCogEngine = None
        logger.exception("Could not bind PackyCogEngine from packy_cog_engine")
else:
    logger.info("PackyCogEngine not available; cognition features disabled until present.")


def _default_get_snark_lines(n: int = 3) -> List[str]:
    samples = [
        "Packy: back when floppies mattered...",
        "If this breaks, blame the meatbag.",
        "I survived firmware updates and so will this script.",
        "Why do you ask me to do obvious things? Fine.",
    ]
    return [random.choice(samples) for _ in range(n)]


def _default_generate_script(kind: str, task_description: str) -> str:
    header = (
        "# -------------------------------------------------------------\n"
        f"# Packy War-Story: {random.choice(['Thermal Martyrdom', 'BIOS Flashback', 'Pizza Incident'])}\n"
        f"# Task: {task_description}\n"
        "# Packy: auto-generated fallback header\n"
        "# -------------------------------------------------------------\n\n"
    )
    body_map = {
        "python": f'#!/usr/bin/env python3\nprint("Running: {task_description}")\n',
        "bash": f'#!/bin/bash\necho "Running: {task_description}"\n',
        "powershell": f'Write-Output "Running: {task_description}"\n',
    }
    body = body_map.get(kind.lower(), f"# Task: {task_description}\n")
    return header + body
