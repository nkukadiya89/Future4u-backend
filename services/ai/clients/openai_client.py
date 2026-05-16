from __future__ import annotations

import os

from decouple import config

from services.ai.exceptions import AIConfigurationError

_CONFIGURED = False


def configure_langsmith() -> None:
    """Apply LangSmith tracing env vars once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    tracing = str(config("LANGCHAIN_TRACING_V2", default="false")).lower() in (
        "1",
        "true",
        "yes",
    )
    if tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        api_key = config("LANGCHAIN_API_KEY", default="")
        if api_key:
            os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_PROJECT"] = config(
            "LANGCHAIN_PROJECT", default="future4u"
        )

    _CONFIGURED = True


def get_openai_api_key() -> str:
    key = config("OPENAI_API_KEY", default="").strip()
    if not key:
        raise AIConfigurationError("OPENAI_API_KEY is not configured")
    return key


def get_chat_model():
    """Centralized LangChain chat model (gpt-4.1-mini, low temperature)."""
    configure_langsmith()
    api_key = get_openai_api_key()

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise AIConfigurationError(
            "langchain-openai is not installed. Run: pip install -r requirements.txt"
        ) from exc

    model_name = config("OPENAI_MODEL", default="gpt-4.1-mini")
    temperature = config("OPENAI_TEMPERATURE", default=0.2, cast=float)

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        max_retries=2,
        api_key=api_key,
    )
