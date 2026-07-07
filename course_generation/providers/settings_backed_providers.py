from __future__ import annotations

from django.conf import settings

from course_generation.exceptions import CourseGenerationConfigurationError
from course_generation.providers.base import LLMProvider


class _SettingsBackedProvider(LLMProvider):
    """Base for providers that read API key and model from Django settings."""

    provider_key: str = ""
    api_key_setting: str = ""
    model_setting: str = ""
    import_error_message: str = ""
    langchain_import_path: tuple[str, str] = ("", "")

    def provider_name(self) -> str:
        return self.provider_key

    def is_configured(self) -> bool:
        return bool(getattr(settings, self.api_key_setting, "") or "")

    def get_chat_model(self, *, max_tokens: int | None = None):
        if not self.is_configured():
            raise CourseGenerationConfigurationError(
                f"{self.api_key_setting} is not configured"
            )

        module_name, class_name = self.langchain_import_path
        try:
            module = __import__(module_name, fromlist=[class_name])
            model_cls = getattr(module, class_name)
        except ImportError as exc:
            raise CourseGenerationConfigurationError(self.import_error_message) from exc

        api_key = getattr(settings, self.api_key_setting, "")
        model_name = getattr(settings, self.model_setting, "")
        temperature = float(getattr(settings, "COURSE_GENERATION_TEMPERATURE", 0.2))
        token_limit = int(
            max_tokens or settings.COURSE_GENERATION_MAX_TOKENS
        )

        return model_cls(
            model=model_name,
            temperature=temperature,
            max_tokens=token_limit,
            api_key=api_key,
        )


class OpenAIProvider(_SettingsBackedProvider):
    provider_key = "openai"
    api_key_setting = "OPENAI_API_KEY"
    model_setting = "OPENAI_MODEL"
    import_error_message = (
        "langchain-openai is not installed. Run: pip install langchain-openai"
    )
    langchain_import_path = ("langchain_openai", "ChatOpenAI")


class GeminiProvider(_SettingsBackedProvider):
    provider_key = "gemini"
    api_key_setting = "GEMINI_API_KEY"
    model_setting = "GEMINI_MODEL"
    import_error_message = (
        "langchain-google-genai is not installed. "
        "Run: pip install langchain-google-genai"
    )
    langchain_import_path = ("langchain_google_genai", "ChatGoogleGenerativeAI")
