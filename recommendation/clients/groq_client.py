from __future__ import annotations

from django.conf import settings

from recommendation.clients.openai_client import configure_langsmith
from recommendation.config import groq_api_key
from recommendation.exceptions import AIConfigurationError


def get_groq_api_key_optional() -> str:
    return groq_api_key()


def get_groq_api_key() -> str:
    key = get_groq_api_key_optional()
    if not key:
        raise AIConfigurationError("GROQ_API_KEY is not configured")
    return key


def get_groq_chat_model():
    """LangChain chat model for Groq (structured output compatible)."""
    configure_langsmith()
    api_key = get_groq_api_key()

    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:
        raise AIConfigurationError(
            "langchain-groq is not installed. Run: pip install -r requirements.txt"
        ) from exc

    model_name = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    temperature = float(getattr(settings, "GROQ_TEMPERATURE", 0))

    return ChatGroq(
        model=model_name,
        temperature=temperature,
        max_retries=2,
        api_key=api_key,
    )
