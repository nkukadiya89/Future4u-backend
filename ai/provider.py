from __future__ import annotations

from typing import Any

from ai.config import (
    groq_api_key,
    is_configured,
    llm_provider,
    model_name,
    reasoning_effort,
    default_temperature,
)
from ai.exceptions import AIConfigurationError


def ensure_configured() -> None:
    if not is_configured():
        provider = llm_provider()
        raise AIConfigurationError(
            f"No AI provider configured for '{provider}'. "
            f"Set {provider.upper()}_API_KEY in .env"
        )


def get_chat_model(*, max_tokens: int | None = None, temperature: float | None = None) -> Any:
    provider = llm_provider()
    if provider == "groq":
        return _build_groq_model(max_tokens=max_tokens, temperature=temperature)
    raise AIConfigurationError(f"Unsupported LLM_PROVIDER '{provider}'. Supported: groq")


def _build_groq_model(*, max_tokens: int | None = None, temperature: float | None = None) -> Any:
    api_key = groq_api_key()
    if not api_key:
        raise AIConfigurationError("GROQ_API_KEY is not configured")

    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:
        raise AIConfigurationError(
            "langchain-groq is not installed. Run: pip install -r requirements.txt"
        ) from exc

    model = model_name()
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature if temperature is not None else default_temperature(),
        "max_tokens": int(max_tokens or 3000),
        "max_retries": 2,
        "api_key": api_key,
    }
    if model.startswith("openai/gpt-oss"):
        kwargs["reasoning_effort"] = reasoning_effort()

    return ChatGroq(**kwargs)
