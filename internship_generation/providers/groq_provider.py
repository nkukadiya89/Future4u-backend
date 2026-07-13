from __future__ import annotations

from django.conf import settings

from internship_generation.config import groq_api_key
from internship_generation.exceptions import InternshipGenerationConfigurationError
from internship_generation.providers.base import LLMProvider


class GroqProvider(LLMProvider):
    def provider_name(self) -> str:
        return "groq"

    def is_configured(self) -> bool:
        return bool(groq_api_key())

    def get_chat_model(self, *, max_tokens: int | None = None):
        if not self.is_configured():
            raise InternshipGenerationConfigurationError(
                "GROQ_API_KEY is not configured"
            )

        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise InternshipGenerationConfigurationError(
                "langchain-groq is not installed. Run: pip install -r requirements.txt"
            ) from exc

        model_name = getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")
        kwargs = {
            "model": model_name,
            "temperature": float(getattr(settings, "GROQ_TEMPERATURE", 0.2)),
            "max_tokens": int(max_tokens or settings.INTERNSHIP_GENERATION_MAX_TOKENS),
            "max_retries": 2,
            "api_key": groq_api_key(),
        }
        if model_name.startswith("openai/gpt-oss"):
            kwargs["reasoning_effort"] = str(
                getattr(settings, "GROQ_REASONING_EFFORT", "low") or "low"
            )

        return ChatGroq(**kwargs)
