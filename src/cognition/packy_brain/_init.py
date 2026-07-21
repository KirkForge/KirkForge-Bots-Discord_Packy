"""PackyInitMixin — class construction + persona/lore/memory bootstrap.

Extracted from packy_brain.py lines 108-332. The __init__ here is the one
Python's MRO will call (it appears first in PackyBrain's mixin order in
__init__.py), and it sets every self.X attribute the other mixin methods
expect to find.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from ._setup import (
    CORE_DIR,
    ROOT_DIR,
    PackyCogEngine,
    _memory_adapter_module,
    _packy_memory_module,
    _persist_module,
    _persona_module,
    _snark_modules,
)

logger = logging.getLogger("packy.brain.init")


class PackyInitMixin:
    VERSION = "2.05"

    def __init__(self, load_on_init: bool = True):
        self.mood: str = "grumpy"
        self.mode: str = "passive"
        self.snark_level: float = 1.0
        self.energy: int = 80
        self.focus: int = 80

        self.persona: Optional[Any] = None
        self.voice_profile: Dict[str, Any] = {}

        self.static_lore_raw: List[str] = []
        self.structured_lore: Dict[str, Any] = {}
        self.lore_loaded_from_structured: bool = False

        self.unfinished_snark: List[str] = []

        self.memory = None
        self.memory_adapter = None

        self.snark_engine = _snark_modules.get("snark_engine")
        self.snark = _snark_modules.get("snark")
        self.teaching = _snark_modules.get("teaching")
        self.lore_writer = _snark_modules.get("lore_writer")
        self.bash_gen = _snark_modules.get("bash_gen")
        self.python_gen = _snark_modules.get("python_gen")
        self.pwsh_gen = _snark_modules.get("pwsh_gen")
        self.actions = _snark_modules.get("actions")
        self.memory_tools = _snark_modules.get("memory_tools")
        self.persona_tools = _snark_modules.get("persona_tools")
        self.behavior_profiles = _snark_modules.get("behavior_profiles")

        self.cog: Optional[Any] = None
        if PackyCogEngine:
            try:
                self.cog = PackyCogEngine(self)
                logger.info("PackyCogEngine initialized and attached to brain")
            except Exception:
                logger.exception("Failed to initialize PackyCogEngine")
                self.cog = None

        self._loaded_static = False
        self._loaded_dynamic = False

        self.trigger_map: Dict[str, List[str]] = {}
        self.profanity_map: Dict[re.Pattern, float] = {}
        self.category_counts: Dict[str, int] = {}

        if load_on_init:
            self.load_persona()
            self.load_structured_lore()
            self.load_dynamic_lore()

    def load_persona(self):
        try:
            if _persona_module and hasattr(_persona_module, "Persona"):
                self.persona = _persona_module.Persona()
                logger.info("Loaded Persona from packy_persona")
            else:
                self.persona = {"name": "Packard Bell", "style": "grumpy"}
                logger.info("Using fallback persona")
        except Exception:
            logger.exception("Failed initializing persona; using fallback")
            self.persona = {"name": "Packard Bell", "style": "grumpy"}

        voice_path = CORE_DIR / "packy_voice_profile.json"
        if voice_path.exists():
            try:
                self.voice_profile = json.loads(voice_path.read_text(encoding="utf-8"))
                logger.info("Loaded voice profile")
            except Exception:
                logger.exception("Failed to parse voice profile; using defaults")
                self.voice_profile = {}
        else:
            self.voice_profile = {}

    def load_structured_lore(self):
        candidates = [
            CORE_DIR / "packy_lorebook_structured.json",
            ROOT_DIR / "data" / "lorebook" / "packy_lorebook_structured.json",
            CORE_DIR / "packy_lorebook_master.json",
        ]
        loaded = False
        for p in candidates:
            try:
                if not p.exists():
                    continue
                raw = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and ("categories" in raw and "triggers" in raw):
                    self.structured_lore = raw
                    self.lore_loaded_from_structured = True
                    logger.info("Loaded structured lorebook from %s", p)
                else:
                    if isinstance(raw, dict) and "lore" in raw and isinstance(raw["lore"], list):
                        self.static_lore_raw = raw["lore"]
                    elif isinstance(raw, list):
                        self.static_lore_raw = raw
                    else:
                        vals = []
                        if isinstance(raw, dict):
                            for v in raw.values():
                                if isinstance(v, list):
                                    for it in v:
                                        if isinstance(it, str):
                                            vals.append(it)
                        self.static_lore_raw = vals
                    logger.info("Loaded legacy-style lorebook from %s", p)
                loaded = True
                break
            except Exception:
                logger.exception("Failed reading lore %s", p)
                continue

        if not loaded:
            logger.warning("No lorebook JSON found; using minimal structured fallback")
            self.structured_lore = {
                "categories": {},
                "triggers": {},
                "meta_hidden": [],
                "stats": {},
            }
            self.lore_loaded_from_structured = False

        if self.lore_loaded_from_structured:
            try:
                self.trigger_map = self.structured_lore.get("triggers", {}) or {}
                cats = self.structured_lore.get("categories", {}) or {}
                self.category_counts = {k: len(v) for k, v in cats.items()}
                logger.info("Structured lore categories loaded: %s", list(cats.keys()))
            except Exception:
                logger.exception("Error processing structured lore; falling back")
                self.trigger_map = {}
                self.category_counts = {}
        else:
            if self.static_lore_raw:
                self.structured_lore = {
                    "categories": {"misc_packyisms": self.static_lore_raw},
                    "triggers": {},
                    "meta_hidden": [],
                    "stats": {"total_entries": len(self.static_lore_raw)},
                }
                self.trigger_map = {}
                self.category_counts = {"misc_packyisms": len(self.static_lore_raw)}
                logger.info(
                    "Fallback lore loaded with %d legacy entries", len(self.static_lore_raw)
                )

        self._init_profanity_map()

    def _init_profanity_map(self):
        raw_map = {
            r"\bdamn\b": 0.5,
            r"\bcrap\b": 0.5,
            r"\bhell\b": 0.5,
            r"\bshit\b": 1.0,
            r"\bbullshit\b": 1.0,
            r"\bpissed\b": 1.0,
            r"\bfuck\b": 1.5,
            r"\bfucking\b": 1.5,
            r"\bfucked\b": 1.5,
            r"\bmotherfucker\b": 1.5,
        }
        self.profanity_map = {}
        for pat, w in raw_map.items():
            try:
                self.profanity_map[re.compile(pat, flags=re.IGNORECASE)] = float(w)
            except Exception:
                logger.debug("Failed compiling profanity pattern: %s", pat)

    def load_dynamic_lore(self):
        if _persist_module and hasattr(_persist_module, "load_all"):
            try:
                result = _persist_module.load_all()
                self.memory = result
                if _memory_adapter_module and hasattr(_memory_adapter_module, "MemoryAdapter"):
                    try:
                        self.memory_adapter = _memory_adapter_module.MemoryAdapter(result)
                    except Exception:
                        logger.exception("MemoryAdapter init failed; continuing with raw memory")
                        self.memory_adapter = None
                logger.info("Loaded dynamic lore via persistent.persistant_loader")
            except Exception:
                logger.exception("persistent.persistant_loader.load_all failed")
                self.memory = None
                self.memory_adapter = None
        elif _packy_memory_module and hasattr(_packy_memory_module, "PackyMemory"):
            try:
                self.memory = _packy_memory_module.PackyMemory()
                if _memory_adapter_module and hasattr(_memory_adapter_module, "MemoryAdapter"):
                    try:
                        self.memory_adapter = _memory_adapter_module.MemoryAdapter(self.memory)
                    except Exception:
                        logger.exception("MemoryAdapter init failed for PackyMemory")
                        self.memory_adapter = None
                logger.info("Initialized persistent.packy_memory.PackyMemory instance")
            except Exception:
                logger.exception("Failed to initialize PackyMemory instance")
                self.memory = None
                self.memory_adapter = None
        else:
            logger.info("No persistent loader or PackyMemory available; dynamic lore disabled")
            self.memory = None
            self.memory_adapter = None

        self._loaded_dynamic = True
