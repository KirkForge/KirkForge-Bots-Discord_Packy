"""PackyScriptsMixin — python/bash/powershell script generators.

Extracted from packy_brain.py lines 634-659.
"""

from __future__ import annotations

import logging

from ._setup import _default_generate_script, logger

logger = logging.getLogger("packy.brain.scripts")


class PackyScriptsMixin:
    def generate_python_script(self, task_description: str) -> str:
        try:
            if self.python_gen and hasattr(self.python_gen, "generate_python_script"):
                return self.python_gen.generate_python_script(task_description)
        except Exception:
            logger.exception("python_gen.generate_python_script failed; using fallback")
        return _default_generate_script("python", task_description)

    def generate_bash_script(self, task_description: str) -> str:
        try:
            if self.bash_gen and hasattr(self.bash_gen, "generate_bash_script"):
                return self.bash_gen.generate_bash_script(task_description)
        except Exception:
            logger.exception("bash_gen.generate_bash_script failed; using fallback")
        return _default_generate_script("bash", task_description)

    def generate_powershell_script(self, task_description: str) -> str:
        try:
            if self.pwsh_gen and hasattr(self.pwsh_gen, "generate_powershell_script"):
                return self.pwsh_gen.generate_powershell_script(task_description)
        except Exception:
            logger.exception("pwsh_gen.generate_powershell_script failed; using fallback")
        return _default_generate_script("powershell", task_description)
