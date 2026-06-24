"""
packy_comment_snark.py — redirect shim

This module was identical to packy_snark.py. Consolidated to avoid drift.
All callers should import from packy_snark directly.
"""
from packy_snark import get_snark_lines

# Alias used by packy_brain.generate_code_from_instruction
get_comment_snark_lines = get_snark_lines

__all__ = ["get_snark_lines", "get_comment_snark_lines"]
