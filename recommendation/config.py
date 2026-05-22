from __future__ import annotations

from django.conf import settings

TOP_SUGGESTION_COUNT = 3
EASY_DECISION_COUNT = 3
# Easy Decision cards only compare the top two ranked careers.
EASY_DECISION_CAREER_COUNT = 2


def groq_api_key() -> str:
    return getattr(settings, "GROQ_API_KEY", "") or ""


def ai_use_openai() -> bool:
    """When False, the AI recommendations endpoint is disabled."""
    return bool(getattr(settings, "AI_USE_OPENAI", True))


def ai_llm_enabled() -> bool:
    """Groq LLM is configured and recommendations are enabled."""
    return ai_use_openai() and bool(groq_api_key())
