"""Tests for LLM default configuration (OpenRouter)."""

from summarizer import DEFAULT_LLM_MODEL, DEFAULT_OPENAI_BASE_URL, Summarizer


def test_openrouter_default_constants():
    assert DEFAULT_OPENAI_BASE_URL == "https://openrouter.ai/api/v1"
    assert DEFAULT_LLM_MODEL == "google/gemini-2.0-flash-001"


def test_summarizer_uses_openrouter_model_without_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_FAST_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_ADVANCED_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    s = Summarizer()
    assert s.fast_model == DEFAULT_LLM_MODEL
    assert s.advanced_model == DEFAULT_LLM_MODEL


def test_summarizer_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "anthropic/claude-3.5-sonnet")
    s = Summarizer()
    assert s.fast_model == "anthropic/claude-3.5-sonnet"
    assert s.advanced_model == "anthropic/claude-3.5-sonnet"
