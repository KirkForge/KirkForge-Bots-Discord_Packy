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
    try:
        from src.cognition.packy_brain import PackyBrain
        print("TEST 1 - Import PackyBrain: PASS")
        return True
    except Exception as e:
        print(f"TEST 1 - Import PackyBrain: FAIL ({e})")
        return False

def test_import_resolve_packy_state():
    """Test 2: Import resolve_packy_state from src.cognition.packy_mood_engine"""
    try:
        from src.cognition.packy_mood_engine import resolve_packy_state
        print("TEST 2 - Import resolve_packy_state: PASS")
        return True
    except Exception as e:
        print(f"TEST 2 - Import resolve_packy_state: FAIL ({e})")
        return False

def test_resolve_packy_state_returns_dict():
    """Test 3: resolve_packy_state(cpu_pct=75, temp_c=28) returns dict with 'mood' key"""
    try:
        from src.cognition.packy_mood_engine import resolve_packy_state
        result = resolve_packy_state(cpu_pct=75, temp_c=28)

        # Check it's a dict
        if not isinstance(result, dict):
            print(f"TEST 3 - resolve_packy_state returns dict: FAIL (returned {type(result)})")
            return False

        # Check for 'mood' key
        if 'mood' not in result:
            print(f"TEST 3 - resolve_packy_state returns dict with 'mood' key: FAIL (keys: {list(result.keys())})")
            return False

        print(f"TEST 3 - resolve_packy_state returns dict with 'mood' key: PASS (mood={result['mood']})")
        return True
    except Exception as e:
        print(f"TEST 3 - resolve_packy_state returns dict with 'mood' key: FAIL ({e})")
        return False

def test_instantiate_packy_brain():
    """Test 4: Instantiate PackyBrain() without crash"""
    try:
        from src.cognition.packy_brain import PackyBrain
        brain = PackyBrain(load_on_init=True)

        if not isinstance(brain, PackyBrain):
            print(f"TEST 4 - Instantiate PackyBrain: FAIL (created {type(brain)})")
            return False

        print("TEST 4 - Instantiate PackyBrain: PASS")
        return True
    except Exception as e:
        print(f"TEST 4 - Instantiate PackyBrain: FAIL ({e})")
        return False

def test_import_packy_cog_engine():
    """Test 5: Import PackyCogEngine from src.cognition.packy_cog_engine"""
    try:
        from src.cognition.packy_cog_engine import PackyCogEngine
        print("TEST 5 - Import PackyCogEngine: PASS")
        return True
    except Exception as e:
        print(f"TEST 5 - Import PackyCogEngine: FAIL ({e})")
        return False

def test_cog_think_returns_string():
    """Test 6: cog.think("write a bash script") returns a non-empty string"""
    try:
        from src.cognition.packy_cog_engine import PackyCogEngine
        cog = PackyCogEngine(brain=None)

        result = cog.think("write a bash script")

        if not isinstance(result, str):
            print(f"TEST 6 - cog.think returns string: FAIL (returned {type(result)})")
            return False

        if len(result) == 0:
            print(f"TEST 6 - cog.think returns non-empty string: FAIL (empty result)")
            return False

        print(f"TEST 6 - cog.think returns non-empty string: PASS (length={len(result)})")
        return True
    except Exception as e:
        print(f"TEST 6 - cog.think returns non-empty string: FAIL ({e})")
        return False

def main():
    """Run all tests and report results"""
    print("=" * 60)
    print("Packy V2.0.0 Cognition Layer Integration Tests")
    print("=" * 60)
    print()

    tests = [
        test_import_packy_brain,
        test_import_resolve_packy_state,
        test_resolve_packy_state_returns_dict,
        test_instantiate_packy_brain,
        test_import_packy_cog_engine,
        test_cog_think_returns_string,
    ]

    results = []
    for test_func in tests:
        results.append(test_func())
        print()

    # Summary
    passed = sum(results)
    total = len(results)
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
