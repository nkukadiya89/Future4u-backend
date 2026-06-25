from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract LLM provider for course generation."""

    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier (e.g. groq, openai)."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when required credentials/settings are present."""

    @abstractmethod
    def get_chat_model(self, *, max_tokens: int | None = None) -> Any:
        """Return a LangChain-compatible chat model."""
