from __future__ import annotations

from django.conf import settings

TOP_SUGGESTION_COUNT = 3


def groq_api_key() -> str:
    return getattr(settings, "GROQ_API_KEY", "") or ""


def ai_use_openai() -> bool:
    """When False, the AI recommendations endpoint is disabled."""
    return bool(getattr(settings, "AI_USE_OPENAI", True))


def ai_llm_enabled() -> bool:
    """Groq LLM is configured and recommendations are enabled."""
    return ai_use_openai() and bool(groq_api_key())
