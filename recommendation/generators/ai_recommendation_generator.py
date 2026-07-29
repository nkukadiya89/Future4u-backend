from __future__ import annotations

import logging
from typing import Any, Callable

from django.conf import settings
from pydantic import ValidationError

from ai.provider import get_chat_model
from recommendation.engine._shared import (
    format_llm_error,
    is_invalid_model_output,
    is_retryable_generation_error,
    payload_gaps,
)
from recommendation.exceptions import AIGenerationError
from recommendation.pipeline.payload_validator import parse_ai_payload
from recommendation.pipeline.validated_payload_normalizer import normalize_payload
from recommendation.schemas.recommendation_output import AIRecommendationPayload
from utils.token_usage import extract_token_usage

logger = logging.getLogger(__name__)


class RecommendationGenerator:
    """LLM call: structured_assessment -> career recommendations (profile-agnostic)."""

    @classmethod
    def generate(
        cls,
        *,
        structured_assessment: dict[str, Any],
        build_prompt: Callable,
        format_inputs: Callable,
    ) -> tuple[AIRecommendationPayload, int]:
        prompt = build_prompt()
        llm = get_chat_model(max_tokens=getattr(settings, "GROQ_MAX_TOKENS", 4400))
        last_error: AIGenerationError | None = None
        validation_feedback = None
        for attempt in range(2):
            try:
                inputs = format_inputs(
                    structured_assessment,
                    validation_feedback=validation_feedback,
                )
                return cls._invoke_once(prompt=prompt, inputs=inputs, llm=llm)
            except AIGenerationError as exc:
                last_error = exc
                if not is_retryable_generation_error(exc) or attempt == 1:
                    raise
                validation_feedback = _clip_feedback(str(exc))
                logger.warning(
                    "Retrying AI recommendation after: %s", validation_feedback
                )

        raise last_error or AIGenerationError("AI recommendation failed")

    @classmethod
    def _invoke_once(
        cls, *, prompt, inputs: dict[str, Any], llm
    ) -> tuple[AIRecommendationPayload, int]:
        """Exactly one LLM call per attempt."""
        try:
            chain = prompt | llm
            ai_message = chain.invoke(inputs)
            token_usage = extract_token_usage(ai_message)

            raw_text = ai_message.content
            if not raw_text or not raw_text.strip():
                raise AIGenerationError("Empty response from AI")

            result = AIRecommendationPayload.model_validate_json(raw_text)
        except ValidationError as exc:
            logger.warning("LLM output validation failed: %s", exc)
            raise AIGenerationError(
                "AI response did not meet the required recommendation schema. "
                f"Details: {exc}"
            ) from exc
        except Exception as exc:
            logger.exception("LLM recommendation generation failed")
            if is_invalid_model_output(exc):
                raise AIGenerationError("AI response failed validation") from exc
            raise AIGenerationError(format_llm_error(exc)) from exc

        try:
            raw = parse_ai_payload(result)
            payload = normalize_payload(raw)
        except ValidationError as exc:
            logger.warning("LLM output validation failed: %s", exc)
            raise AIGenerationError(
                "AI response did not meet the required recommendation schema. "
                f"Details: {exc}"
            ) from exc

        gaps = payload_gaps(payload)
        if gaps:
            logger.warning("AI payload shape gaps: %s", "; ".join(gaps))
            raise AIGenerationError(
                "AI response did not meet the required recommendation schema. "
                f"Details: {'; '.join(gaps)}"
            )
        return payload, token_usage


def _clip_feedback(message: str) -> str:
    text = " ".join(message.split())
    if len(text) <= 240:
        return text
    return text[:237].rstrip() + "..."
