from __future__ import annotations

import logging
from typing import Any

from internship_generation.config import ai_llm_enabled
from internship_generation.exceptions import (
    InternshipGenerationConfigurationError,
    InternshipGenerationValidationError,
)
from internship_generation.prompts.internship_generation_prompt import (
    build_internship_generation_prompt,
    format_prompt_inputs,
)
from internship_generation.providers.factory import ensure_ai_provider_configured, get_llm_provider
from internship_generation.schemas.internship_output import InternshipGenerationPayload
from internship_generation.services.json_response_parser import JsonResponseParser

logger = logging.getLogger(__name__)

_MAX_GENERATION_ATTEMPTS = 3


class InternshipGenerator:
    """Single LLM invocation: internship overview input -> structured internship details."""

    @classmethod
    def generate(cls, *, generation_input: dict[str, Any]) -> InternshipGenerationPayload:
        if not ai_llm_enabled():
            raise InternshipGenerationConfigurationError(
                "AI internship generation is temporarily unavailable"
            )
        ensure_ai_provider_configured()

        prompt = build_internship_generation_prompt()
        llm = get_llm_provider().get_chat_model()
        parser = JsonResponseParser()
        last_error: InternshipGenerationValidationError | None = None
        validation_feedback = "None"

        for attempt in range(_MAX_GENERATION_ATTEMPTS):
            try:
                inputs = format_prompt_inputs(
                    generation_input={**generation_input, "validation_feedback": validation_feedback}
                )
                return cls._invoke_once(
                    prompt=prompt,
                    inputs=inputs,
                    llm=llm,
                    parser=parser,
                )
            except InternshipGenerationValidationError as exc:
                last_error = exc
                validation_feedback = _clip_feedback(exc.details)
                if not _is_retryable_generation_error(exc) or attempt == _MAX_GENERATION_ATTEMPTS - 1:
                    raise
                logger.warning(
                    "Retrying internship generation after %s (attempt %s/%s)",
                    exc.error,
                    attempt + 2,
                    _MAX_GENERATION_ATTEMPTS,
                )

        raise last_error or InternshipGenerationValidationError(
            "Internship generation failed",
            error="Validation failed",
            details="Internship generation failed after retries",
        )

    @classmethod
    def _invoke_once(
        cls,
        *,
        prompt,
        inputs: dict[str, str],
        llm,
        parser: JsonResponseParser,
    ) -> InternshipGenerationPayload:
        try:
            chain = prompt | llm
            result = chain.invoke(inputs)
            raw_text = _extract_text_content(result)
        except Exception as exc:
            logger.exception("LLM internship generation failed")
            raise InternshipGenerationValidationError(
                _format_llm_error(exc),
                error="LLM request failed",
                details=_format_llm_error(exc),
            ) from exc

        parse_result = parser.parse_and_validate(
            raw_text, model_class=InternshipGenerationPayload
        )
        if parse_result.success and parse_result.validated_model is not None:
            return parse_result.validated_model  # type: ignore[return-value]

        if parse_result.is_json_parse_failure:
            details = parse_result.parse_error or "Invalid JSON in LLM response"
            raise InternshipGenerationValidationError(
                details,
                error="JSON parsing failed",
                details=details,
            )

        details = parse_result.validation_errors or "Schema validation failed"
        raise InternshipGenerationValidationError(
            details,
            error="Schema validation failed",
            details=details,
        )


def _extract_text_content(result: Any) -> str:
    if isinstance(result, str):
        return result

    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif hasattr(block, "text"):
                parts.append(str(block.text))
        return "".join(parts)
    return str(result)


def _format_llm_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    if "insufficient_quota" in lowered or "quota" in lowered or "429" in lowered:
        return "Internship generation is busy right now. Please try again shortly."
    return "Unable to generate internship details right now. Please try again."


def _is_retryable_generation_error(exc: InternshipGenerationValidationError) -> bool:
    return exc.error in ("JSON parsing failed", "Schema validation failed")


def _clip_feedback(message: str) -> str:
    text = " ".join(message.split())
    if len(text) <= 240:
        return text
    return text[:237].rstrip() + "..."
