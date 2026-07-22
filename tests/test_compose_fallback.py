"""Tests for PackyCogEngine emergency fallback behavior (ADR-018)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.cognition.packy_cog_engine import PackyCogEngine


class TestPackyCogEngineEmergencyFallback:
    """When call_llm fails, the emergency composer provides a template response."""

    def test_think_returns_string(self):
        """think() always returns a non-empty string (emergency fallback)."""
        engine = PackyCogEngine(brain=None)
        result = engine.think("hello")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_think_general_intent(self):
        """General intent produces a response with the input text."""
        engine = PackyCogEngine(brain=None)
        result = engine.think("what is the weather")
        assert "what is the weather" in result

    def test_think_code_intent(self):
        """Code intent produces a response mentioning the language."""
        engine = PackyCogEngine(brain=None)
        result = engine.think("write a python script")
        assert "python" in result.lower()

    def test_think_explain_intent(self):
        """Explain intent produces a response."""
        engine = PackyCogEngine(brain=None)
        result = engine.think("explain how DNS works")
        assert isinstance(result, str)
        assert len(result) > 50

    def test_composer_is_deterministic_in_intent(self):
        """Interpret is deterministic (no randomness)."""
        engine = PackyCogEngine(brain=None)
        result1 = engine.interpret("write a python function")
        result2 = engine.interpret("write a python function")
        assert result1["intent"] == result2["intent"]
        assert result1["intent"] == "code"

    def test_create_lore_entry(self):
        """create_lore_entry returns a lore-formatted string."""
        engine = PackyCogEngine(brain=None)
        result = engine.create_lore_entry("packy survived a thermal event")
        assert "packy survived a thermal event" in result
        assert "Lore Entry" in result

    def test_reflect_on_memory_empty(self):
        """reflect_on_memory with empty list returns a default message."""
        engine = PackyCogEngine(brain=None)
        result = engine.reflect_on_memory([])
        assert "no memories" in result.lower()

    def test_reflect_on_memory_nonempty(self):
        """reflect_on_memory with memories returns a reflection."""
        engine = PackyCogEngine(brain=None)
        result = engine.reflect_on_memory([{"text": "thermal meltdown"}])
        assert "thermal meltdown" in result


class TestPackyCogEngineDocstring:
    """Verify docstrings are honest about emergency-only status."""

    def test_class_docstring_says_emergency(self):
        """Class docstring must mention 'emergency' or 'fallback'."""
        doc = PackyCogEngine.__doc__
        assert doc is not None
        doc_lower = doc.lower()
        assert "emergency" in doc_lower or "fallback" in doc_lower

    def test_module_docstring_says_emergency(self):
        """Module docstring must mention 'emergency' or 'fallback'."""
        from src.cognition import packy_cog_engine

        doc = packy_cog_engine.__doc__
        assert doc is not None
        doc_lower = doc.lower()
        assert "emergency" in doc_lower or "fallback" in doc_lower
