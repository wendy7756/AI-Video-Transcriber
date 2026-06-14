"""Curated third-party LLM provider and model presets (OpenAI-compatible APIs)."""

from __future__ import annotations

from typing import Any

PROVIDER_PRESETS: list[dict[str, str]] = [
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "hint": "One key, many models (recommended)",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "hint": "https://platform.deepseek.com",
    },
    {
        "id": "siliconflow",
        "name": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "hint": "https://siliconflow.cn",
    },
    {
        "id": "moonshot",
        "name": "Moonshot (Kimi)",
        "base_url": "https://api.moonshot.cn/v1",
        "hint": "https://platform.moonshot.cn",
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "hint": "https://platform.openai.com",
    },
]

# model id, display name, which provider preset ids can use it
RECOMMENDED_MODELS: list[dict[str, Any]] = [
    {
        "id": "google/gemini-2.0-flash-001",
        "name": "Gemini 2.0 Flash",
        "providers": ["openrouter"],
    },
    {
        "id": "anthropic/claude-3.5-sonnet",
        "name": "Claude 3.5 Sonnet",
        "providers": ["openrouter"],
    },
    {
        "id": "openai/gpt-4o-mini",
        "name": "GPT-4o Mini",
        "providers": ["openrouter"],
    },
    {
        "id": "deepseek/deepseek-chat",
        "name": "DeepSeek Chat (via OpenRouter)",
        "providers": ["openrouter"],
    },
    {
        "id": "qwen/qwen-plus",
        "name": "Qwen Plus (via OpenRouter)",
        "providers": ["openrouter"],
    },
    {
        "id": "meta-llama/llama-3.3-70b-instruct",
        "name": "Llama 3.3 70B",
        "providers": ["openrouter"],
    },
    {
        "id": "deepseek-chat",
        "name": "DeepSeek Chat",
        "providers": ["deepseek"],
    },
    {
        "id": "deepseek-reasoner",
        "name": "DeepSeek Reasoner",
        "providers": ["deepseek"],
    },
    {
        "id": "Qwen/Qwen2.5-72B-Instruct",
        "name": "Qwen2.5 72B Instruct",
        "providers": ["siliconflow"],
    },
    {
        "id": "deepseek-ai/DeepSeek-V3",
        "name": "DeepSeek V3",
        "providers": ["siliconflow"],
    },
    {
        "id": "moonshot-v1-8k",
        "name": "Moonshot v1 8K",
        "providers": ["moonshot"],
    },
    {
        "id": "moonshot-v1-32k",
        "name": "Moonshot v1 32K",
        "providers": ["moonshot"],
    },
    {
        "id": "gpt-4o-mini",
        "name": "GPT-4o Mini",
        "providers": ["openai"],
    },
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "providers": ["openai"],
    },
]

DEFAULT_PROVIDER_ID = "openrouter"
DEFAULT_MODEL_ID = "google/gemini-2.0-flash-001"
DEFAULT_LLM_MODEL = DEFAULT_MODEL_ID
DEFAULT_OPENAI_BASE_URL = "https://openrouter.ai/api/v1"


def get_provider(provider_id: str) -> dict[str, str] | None:
    for item in PROVIDER_PRESETS:
        if item["id"] == provider_id:
            return item
    return None


def models_for_provider(provider_id: str) -> list[dict[str, Any]]:
    return [m for m in RECOMMENDED_MODELS if provider_id in m.get("providers", [])]


def llm_presets_payload() -> dict[str, Any]:
    return {
        "default_provider": DEFAULT_PROVIDER_ID,
        "default_model": DEFAULT_MODEL_ID,
        "providers": PROVIDER_PRESETS,
        "recommended_models": RECOMMENDED_MODELS,
    }
