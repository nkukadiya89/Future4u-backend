from __future__ import annotations

from django.conf import settings

from recommendation.config import groq_api_key
from recommendation.exceptions import AIConfigurationError


def get_groq_api_key_optional() -> str:
    return groq_api_key()


def get_groq_api_key() -> str:
    key = get_groq_api_key_optional()
    if not key:
        raise AIConfigurationError("GROQ_API_KEY is not configured")
    return key


def get_groq_chat_model(*, max_tokens: int | None = None):
    """LangChain chat model for Groq AI features."""
    api_key = get_groq_api_key()

    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:
        raise AIConfigurationError(
            "langchain-groq is not installed. Run: pip install -r requirements.txt"
        ) from exc

    model_name = getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")
    kwargs = {
        "model": model_name,
        "temperature": float(getattr(settings, "GROQ_TEMPERATURE", 0.2)),
        "max_tokens": int(max_tokens or getattr(settings, "GROQ_MAX_TOKENS", 4400)),
        "max_retries": 2,
        "api_key": api_key,
    }
    if model_name.startswith("openai/gpt-oss"):
        kwargs["reasoning_effort"] = str(
            getattr(settings, "GROQ_REASONING_EFFORT", "low") or "low"
        )

    return ChatGroq(**kwargs)
