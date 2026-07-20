"""PackyCognitionMixin — thin wrapper around PackyCogEngine (stochastic composer).

Extracted from packy_brain.py lines 692-768.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from ._setup import _default_generate_script, _try_import, logger

logger = logging.getLogger("packy.brain.cognition")


class PackyCognitionMixin:
    def think(self, instruction: str) -> str:
        try:
            if not self.cog:
                logger.warning("Cognition engine not available; returning basic fallback")
                return self._basic_think_fallback(instruction)
            return self.cog.think(instruction)
        except Exception:
            logger.exception("cog.think failed; using fallback")
            return self._basic_think_fallback(instruction)

    def interpret(self, instruction: str) -> dict:
        try:
            if not self.cog:
                return {"raw": instruction, "intent": "general", "needs_code": False}
            return self.cog.interpret(instruction)
        except Exception:
            logger.exception("cog.interpret failed; fallback")
            return {"raw": instruction, "intent": "general", "needs_code": False}

    def plan(self, interpretation: dict) -> dict:
        try:
            if not self.cog:
                return {"strategy": "general", "notes": []}
            return self.cog.plan(interpretation)
        except Exception:
            logger.exception("cog.plan failed; fallback")
            return {"strategy": "general", "notes": []}

    def _basic_think_fallback(self, instruction: str) -> str:
        return f"Packy (fallback) thinks: I heard '{instruction}'. Be more specific."

    def generate_code_from_instruction(self, instruction: str, preferred_language: Optional[str] = None) -> str:
        try:
            interp = self.interpret(instruction)
            plan = self.plan(interp)
            language = preferred_language or interp.get("language") or plan.get("language") or "python"
            task_desc = instruction.strip()
            plan_notes = plan.get("notes") or []
            if plan_notes:
                task_desc = f"{task_desc}\n# plan: " + "; ".join(plan_notes)

            header_snark_lines: List[str] = []
            try:
                comment_snark_module = _try_import("packy_snark")
                if comment_snark_module and hasattr(comment_snark_module, "get_snark_lines"):
                    header_snark_lines = comment_snark_module.get_snark_lines(3)
            except Exception:
                logger.debug("comment_snark lines not available; using fallback")

            if not header_snark_lines:
                header_snark_lines = (self.unfinished_snark[:3] or
                                      self.structured_lore.get("categories", {}).get("misc_packyisms", [])[:3] or [])

            header_block = ""
            if header_snark_lines:
                for l in header_snark_lines:
                    header_block += f"# {l}\n"
                header_block += "\n"

            if language.lower().startswith("py"):
                body = self.generate_python_script(task_desc)
                return header_block + body
            if language.lower().startswith("bash"):
                body = self.generate_bash_script(task_desc)
                return header_block + body
            if language.lower().startswith("ps") or language.lower().startswith("powershell"):
                body = self.generate_powershell_script(task_desc)
                return header_block + body

            return header_block + _default_generate_script(language, task_desc)
        except Exception:
            logger.exception("generate_code_from_instruction failed; falling back to default script")
            return _default_generate_script(preferred_language or "python", instruction)
