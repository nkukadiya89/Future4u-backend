from __future__ import annotations

from typing import Any

from recommendation.clients.groq_client import get_groq_api_key_optional, get_groq_chat_model
from recommendation.exceptions import AIConfigurationError
from recommendation.observability import configure_langsmith_tracing


def ensure_ai_provider_configured() -> None:
    if not get_groq_api_key_optional():
        raise AIConfigurationError(
            "No AI provider configured. Set GROQ_API_KEY in .env"
        )


def get_chat_model(*, max_tokens: int | None = None) -> Any:
    """Return the Groq chat model used by AI features."""
    configure_langsmith_tracing()
    ensure_ai_provider_configured()
    return get_groq_chat_model(max_tokens=max_tokens)
