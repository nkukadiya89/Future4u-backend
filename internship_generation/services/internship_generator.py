from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from ai.config import is_configured
from ai.provider import ensure_configured, get_chat_model
from internship_generation.exceptions import (
    InternshipGenerationConfigurationError,
    InternshipGenerationValidationError,
)
from internship_generation.prompts.internship_generation_prompt import (
    build_internship_generation_prompt,
    format_prompt_inputs,
)
from internship_generation.schemas.internship_output import InternshipGenerationPayload
from internship_generation.services.payload_parser import parse_ai_payload
from utils.token_usage import extract_token_usage

logger = logging.getLogger(__name__)

_MAX_GENERATION_ATTEMPTS = 2


class InternshipGenerator:
    """Single LLM invocation: internship overview input -> structured internship details."""

    @classmethod
    def generate(
        cls, *, generation_input: dict[str, Any]
    ) -> tuple[InternshipGenerationPayload, int]:
        if not is_configured():
            raise InternshipGenerationConfigurationError(
                "AI internship generation is temporarily unavailable"
            )
        ensure_configured()

        prompt = build_internship_generation_prompt()
        llm = get_chat_model()
        last_error: InternshipGenerationValidationError | None = None
        validation_feedback = "None"

        for attempt in range(_MAX_GENERATION_ATTEMPTS):
            try:
                inputs = format_prompt_inputs(
                    generation_input={
                        **generation_input,
                        "validation_feedback": validation_feedback,
                    }
                )
                return cls._invoke_once(
                    prompt=prompt,
                    inputs=inputs,
                    llm=llm,
                )
            except InternshipGenerationValidationError as exc:
                last_error = exc
                validation_feedback = _clip_feedback(exc.details)
                if (
                    not _is_retryable_generation_error(exc)
                    or attempt == _MAX_GENERATION_ATTEMPTS - 1
                ):
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
    ) -> tuple[InternshipGenerationPayload, int]:
        try:
            chain = prompt | llm
            result = chain.invoke(inputs)
            token_usage = extract_token_usage(result)
            raw_text = _extract_text_content(result)
            if not raw_text or not raw_text.strip():
                raise InternshipGenerationValidationError(
                    "Empty response from AI",
                    error="Generation failed",
                    details="AI returned an empty response",
                )

            parsed = json.loads(raw_text)
            if not isinstance(parsed, dict):
                raise InternshipGenerationValidationError(
                    "Response is not a valid JSON object",
                    error="Generation failed",
                    details="AI response root must be a JSON object",
                )

            payload = parse_ai_payload(parsed)
            return payload, token_usage
        except json.JSONDecodeError as exc:
            logger.warning("Internship generation JSON parse failed: %s", exc)
            raise InternshipGenerationValidationError(
                "Unable to generate internship details. Please try again.",
                error="Generation failed",
                details="AI response could not be parsed as valid JSON",
            ) from exc
        except (ValidationError, ValueError) as exc:
            logger.warning("Internship generation validation failed: %s", exc)
            raise InternshipGenerationValidationError(
                str(exc),
                error="Validation failed",
                details=str(exc),
            ) from exc
        except InternshipGenerationValidationError:
            raise
        except Exception as exc:
            logger.exception("LLM internship generation failed")
            raise InternshipGenerationValidationError(
                _format_llm_error(exc),
                error="LLM request failed",
                details=_format_llm_error(exc),
            ) from exc


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
    return exc.error in ("Generation failed", "Validation failed")


def _clip_feedback(message: str) -> str:
    text = " ".join(message.split())
    if len(text) <= 240:
        return text
    return text[:237].rstrip() + "..."
