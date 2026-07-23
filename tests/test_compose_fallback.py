"""Tests for PackyCogEngine emergency fallback behavior (ADR-018)."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.cognition.packy_cog_engine import PackyCogEngine


class TestPackyCogEngineEmergencyFallback:
    """When call_llm fails, the emergency composer provides a template response."""

    def test_think_returns_string(self):
        """think() always returns a non-empty string (template fallback)."""
        engine = PackyCogEngine(brain=None)
        result = asyncio.run(engine.think("hello"))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_think_general_intent(self):
        """General intent produces a response with the input text."""
        engine = PackyCogEngine(brain=None)
        result = asyncio.run(engine.think("what is the weather"))
        assert "what is the weather" in result

    def test_think_code_intent(self):
        """Code intent produces a response mentioning the language."""
        engine = PackyCogEngine(brain=None)
        result = asyncio.run(engine.think("write a python script"))
        assert "python" in result.lower()

    def test_think_explain_intent(self):
        """Explain intent produces a response."""
        engine = PackyCogEngine(brain=None)
        result = asyncio.run(engine.think("explain how DNS works"))
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


class TestPackyCogEngineLLMFallback:
    """Cheap-LLM fallback: when llm_fn is provided and succeeds, it returns
    the LLM output. When llm_fn raises, template fallback fires."""

    def test_llm_fn_returns_response(self):
        """When llm_fn succeeds, think() returns the LLM output."""

        async def mock_llm(system_prompt, user_text, max_tokens=100, model=None):
            return "Mock LLM response for: " + user_text

        engine = PackyCogEngine(brain=None, llm_fn=mock_llm)
        result = asyncio.run(engine.think("hello"))
        assert result == "Mock LLM response for: hello"

    def test_llm_fn_raises_triggers_template_fallback(self):
        """When llm_fn raises, think() falls back to template filling."""

        async def failing_llm(system_prompt, user_text, max_tokens=100, model=None):
            raise RuntimeError("LLM unavailable")

        engine = PackyCogEngine(brain=None, llm_fn=failing_llm)
        result = asyncio.run(engine.think("hello"))
        assert isinstance(result, str)
        assert len(result) > 0
        assert result != "Mock LLM response"

    def test_llm_fn_returns_empty_triggers_template_fallback(self):
        """When llm_fn returns empty string, think() falls back to template."""

        async def empty_llm(system_prompt, user_text, max_tokens=100, model=None):
            return ""

        engine = PackyCogEngine(brain=None, llm_fn=empty_llm)
        result = asyncio.run(engine.think("hello"))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_llm_fn_uses_template(self):
        """Without llm_fn, think() uses template filling (same as before)."""
        engine = PackyCogEngine(brain=None, llm_fn=None)
        result = asyncio.run(engine.think("what is the weather"))
        assert "what is the weather" in result

    def test_llm_fn_receives_compose_model(self):
        """llm_fn is called with the PACKY_COMPOSE_MODEL model name."""
        received_model = None

        async def capture_model(system_prompt, user_text, max_tokens=100, model=None):
            nonlocal received_model
            received_model = model
            return "response"

        engine = PackyCogEngine(brain=None, llm_fn=capture_model)
        engine.compose_model = "test-model-v1"
        asyncio.run(engine.think("hello"))
        assert received_model == "test-model-v1"


class TestPackyCogEngineDocstring:
    """Verify docstrings are honest about cheap-LLM fallback status."""

    def test_class_docstring_says_fallback(self):
        """Class docstring must mention 'fallback'."""
        doc = PackyCogEngine.__doc__
        assert doc is not None
        doc_lower = doc.lower()
        assert "fallback" in doc_lower

    def test_module_docstring_says_fallback(self):
        """Module docstring must mention 'fallback'."""
        from src.cognition import packy_cog_engine

        doc = packy_cog_engine.__doc__
        assert doc is not None
        doc_lower = doc.lower()
        assert "fallback" in doc_lower
