from __future__ import annotations

import logging
from typing import Any, Callable

from pydantic import ValidationError

from recommendation.clients.llm_client import get_chat_model
from recommendation.exceptions import AIGenerationError
from utils.token_usage import extract_token_usage
from recommendation.engine._shared import (
    format_llm_error,
    is_invalid_model_output,
    is_retryable_generation_error,
    payload_gaps,
)
from recommendation.pipeline.validated_payload_normalizer import normalize_payload
from recommendation.pipeline.payload_validator import parse_ai_payload
from recommendation.schemas.recommendation_output import AIRecommendationPayload

logger = logging.getLogger(__name__)


class RecommendationGenerator:
    """LLM call: structured_assessment -> career recommendations (profile-agnostic)."""

    _last_token_usage = 0

    @classmethod
    def generate(
        cls,
        *,
        structured_assessment: dict[str, Any],
        build_prompt: Callable,
        format_inputs: Callable,
    ) -> AIRecommendationPayload:
        prompt = build_prompt()
        inputs = format_inputs(structured_assessment)
        llm = get_chat_model()
        last_error: AIGenerationError | None = None
        for attempt in range(2):
            try:
                return cls._invoke_once(prompt=prompt, inputs=inputs, llm=llm)
            except AIGenerationError as exc:
                last_error = exc
                if not is_retryable_generation_error(exc) or attempt == 1:
                    raise
                logger.warning("Retrying AI recommendation after invalid response")

        raise last_error or AIGenerationError("AI recommendation failed")

    @classmethod
    def _invoke_once(
        cls, *, prompt, inputs: dict[str, Any], llm
    ) -> AIRecommendationPayload:
        """Exactly one provider invocation."""
        try:
            # Make raw LLM call first to capture actual token usage,
            # then use structured output for guaranteed valid JSON parsing.
            raw_chain = prompt | llm
            ai_message = raw_chain.invoke(inputs)
            cls._last_token_usage = extract_token_usage(ai_message)

            # Parse the raw response through structured output for validation
            raw_text = ai_message.content
            if isinstance(raw_text, str) and raw_text.strip():
                # Try direct model parse first
                try:
                    result = AIRecommendationPayload.model_validate_json(raw_text)
                except Exception:
                    # Fall back to structured output
                    structured_llm = llm.with_structured_output(
                        AIRecommendationPayload,
                        method="json_mode",
                    )
                    chain = prompt | structured_llm
                    result = chain.invoke(inputs)
            else:
                structured_llm = llm.with_structured_output(
                    AIRecommendationPayload,
                    method="json_mode",
                )
                chain = prompt | structured_llm
                result = chain.invoke(inputs)
        except ValidationError as exc:
            logger.warning("LLM output validation failed: %s", exc)
            raise AIGenerationError("AI response failed validation") from exc
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
            raise AIGenerationError("AI response failed validation") from exc

        gaps = payload_gaps(payload)
        if gaps:
            logger.warning("AI payload shape gaps: %s", "; ".join(gaps))
            raise AIGenerationError(
                "AI response did not meet the required recommendation schema. "
                f"Details: {'; '.join(gaps)}"
            )
        return payload
