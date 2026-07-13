from __future__ import annotations

from course_generation.config import course_generation_llm_provider
from course_generation.exceptions import CourseGenerationConfigurationError
from course_generation.providers.base import LLMProvider
from course_generation.providers.groq_provider import GroqProvider
from course_generation.providers.settings_backed_providers import (
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
    provider_name = course_generation_llm_provider()
    provider_cls = _PROVIDER_REGISTRY.get(provider_name)
    if provider_cls is None:
        supported = ", ".join(sorted(_PROVIDER_REGISTRY))
        raise CourseGenerationConfigurationError(
            f"Unsupported COURSE_GENERATION_LLM_PROVIDER '{provider_name}'. "
            f"Supported values: {supported}"
        )
    return provider_cls()


def ensure_ai_provider_configured() -> None:
    provider = get_llm_provider()
    if not provider.is_configured():
        raise CourseGenerationConfigurationError(
            f"No AI provider configured for '{provider.provider_name()}'"
        )
