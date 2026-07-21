#!/usr/bin/env python3
"""
Integration test suite for Packy V2.0.0 cognition layer
Tests core imports and functionality before running the bot
"""

import sys
from pathlib import Path

# Add project root to path so imports work from test directory
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def test_import_packy_brain():
    """Test 1: Import PackyBrain from src.cognition.packy_brain"""
    from src.cognition.packy_brain import PackyBrain

    assert PackyBrain is not None


def test_import_resolve_packy_state():
    """Test 2: Import resolve_packy_state from src.cognition.packy_mood_engine"""
    from src.cognition.packy_mood_engine import resolve_packy_state

    assert callable(resolve_packy_state)


def test_resolve_packy_state_returns_dict():
    """Test 3: resolve_packy_state(cpu_pct=75, temp_c=28) returns dict with 'mood' key"""
    from src.cognition.packy_mood_engine import resolve_packy_state

    result = resolve_packy_state(cpu_pct=75, temp_c=28)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "mood" in result, f"Expected 'mood' key, got keys: {list(result.keys())}"


def test_instantiate_packy_brain():
    """Test 4: Instantiate PackyBrain() without crash"""
    from src.cognition.packy_brain import PackyBrain

    brain = PackyBrain(load_on_init=True)
    assert isinstance(brain, PackyBrain), f"Expected PackyBrain, got {type(brain)}"


def test_import_packy_cog_engine():
    """Test 5: Import PackyCogEngine from src.cognition.packy_cog_engine"""
    from src.cognition.packy_cog_engine import PackyCogEngine

    assert PackyCogEngine is not None


def test_cog_think_returns_string():
    """Test 6: cog.think("write a bash script") returns a non-empty string"""
    from src.cognition.packy_cog_engine import PackyCogEngine

    cog = PackyCogEngine(brain=None)
    result = cog.think("write a bash script")
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert len(result) > 0, "Expected non-empty string"
