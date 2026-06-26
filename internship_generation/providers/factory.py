from __future__ import annotations

from internship_generation.config import internship_generation_llm_provider
from internship_generation.exceptions import InternshipGenerationConfigurationError
from internship_generation.providers.base import LLMProvider
from internship_generation.providers.groq_provider import GroqProvider
from internship_generation.providers.settings_backed_providers import (
    GeminiProvider,
    OpenAIProvider,
)

_PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "groq": GroqProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider instance."""
    provider_name = internship_generation_llm_provider()
    provider_cls = _PROVIDER_REGISTRY.get(provider_name)
    if provider_cls is None:
        supported = ", ".join(sorted(_PROVIDER_REGISTRY))
        raise InternshipGenerationConfigurationError(
            f"Unsupported INTERNSHIP_GENERATION_LLM_PROVIDER '{provider_name}'. "
            f"Supported values: {supported}"
        )
    return provider_cls()


def ensure_ai_provider_configured() -> None:
    provider = get_llm_provider()
    if not provider.is_configured():
        raise InternshipGenerationConfigurationError(
            f"No AI provider configured for '{provider.provider_name()}'"
        )
