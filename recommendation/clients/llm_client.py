from __future__ import annotations

from typing import Any

from recommendation.clients.groq_client import get_groq_api_key_optional, get_groq_chat_model
from recommendation.clients.openai_client import configure_langsmith
from recommendation.exceptions import AIConfigurationError


def ensure_ai_provider_configured() -> None:
    if not get_groq_api_key_optional():
        raise AIConfigurationError(
            "No AI provider configured. Set GROQ_API_KEY in .env"
        )


def get_chat_model() -> Any:
    """Return the Groq chat model (LangSmith tracing configured when enabled)."""
    configure_langsmith()
    ensure_ai_provider_configured()
    return get_groq_chat_model()
