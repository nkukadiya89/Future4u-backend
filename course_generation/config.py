from __future__ import annotations

from django.conf import settings


def groq_api_key() -> str:
    return getattr(settings, "GROQ_API_KEY", "") or ""


def course_generation_enabled() -> bool:
    return bool(getattr(settings, "COURSE_GENERATION_ENABLED", True))


def course_generation_llm_provider() -> str:
    return str(getattr(settings, "COURSE_GENERATION_LLM_PROVIDER", "groq")).strip().lower()


def ai_llm_enabled() -> bool:
    """Configured provider is available and course generation is enabled."""
    if not course_generation_enabled():
        return False
    from course_generation.providers.factory import get_llm_provider

    return get_llm_provider().is_configured()
