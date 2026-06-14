"""Tests for third-party LLM preset catalog."""

from llm_presets import (
    DEFAULT_MODEL_ID,
    DEFAULT_PROVIDER_ID,
    llm_presets_payload,
    models_for_provider,
)


def test_payload_includes_providers_and_models():
    data = llm_presets_payload()
    assert data["default_provider"] == DEFAULT_PROVIDER_ID
    assert data["default_model"] == DEFAULT_MODEL_ID
    assert len(data["providers"]) >= 5
    assert len(data["recommended_models"]) >= 10


def test_openrouter_has_gemini_and_claude():
    models = models_for_provider("openrouter")
    ids = {m["id"] for m in models}
    assert "google/gemini-2.0-flash-001" in ids
    assert "anthropic/claude-3.5-sonnet" in ids


def test_deepseek_direct_models():
    models = models_for_provider("deepseek")
    ids = {m["id"] for m in models}
    assert "deepseek-chat" in ids
