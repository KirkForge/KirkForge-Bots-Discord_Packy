"""
packy_snark_engine.py — redirect shim

Originally held a smaller subset of the full snark pool.
Now delegates to packy_snark.py which has the complete pool.
"""
from packy_snark import get_snark_lines, _get_pool

__all__ = ["get_snark_lines", "_get_pool"]
