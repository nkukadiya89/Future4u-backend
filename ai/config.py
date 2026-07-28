from __future__ import annotations

from django.conf import settings


def llm_provider() -> str:
    return str(getattr(settings, "LLM_PROVIDER", "groq")).strip().lower()


def groq_api_key() -> str:
    return getattr(settings, "GROQ_API_KEY", "") or ""


def is_configured() -> bool:
    provider = llm_provider()
    if provider == "groq":
        return bool(groq_api_key())
    return False


def model_name() -> str:
    return (
        getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b").strip()
        or "openai/gpt-oss-120b"
    )


def default_temperature() -> float:
    return float(getattr(settings, "GROQ_TEMPERATURE", 0.2))


def reasoning_effort() -> str:
    return str(getattr(settings, "GROQ_REASONING_EFFORT", "low") or "low").strip()
