from __future__ import annotations

from job_generation.config import job_generation_llm_provider
from job_generation.exceptions import JobGenerationConfigurationError
from job_generation.providers.base import LLMProvider
from job_generation.providers.groq_provider import GroqProvider
from job_generation.providers.stub_providers import GeminiProvider, OpenAIProvider

_PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "groq": GroqProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider instance."""
    provider_name = job_generation_llm_provider()
    provider_cls = _PROVIDER_REGISTRY.get(provider_name)
    if provider_cls is None:
        supported = ", ".join(sorted(_PROVIDER_REGISTRY))
        raise JobGenerationConfigurationError(
            f"Unsupported JOB_GENERATION_LLM_PROVIDER '{provider_name}'. "
            f"Supported values: {supported}"
        )
    return provider_cls()


def ensure_ai_provider_configured() -> None:
    provider = get_llm_provider()
    if not provider.is_configured():
        raise JobGenerationConfigurationError(
            f"No AI provider configured for '{provider.provider_name()}'"
        )
