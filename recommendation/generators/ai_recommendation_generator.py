from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from recommendation.clients.llm_client import get_chat_model
from recommendation.exceptions import AIGenerationError
from recommendation.pipeline.output_normalizer import normalize_payload
from recommendation.pipeline.payload_repair import describe_shape_gaps
from recommendation.pipeline.payload_validator import parse_ai_payload, parse_ai_payload_lenient
from recommendation.prompts.ai_recommendation_prompt import (
    build_recommendation_prompt,
    format_prompt_inputs,
)
from recommendation.schemas.recommendation_output import AIRecommendationPayload

logger = logging.getLogger(__name__)


class AIRecommendationGenerator:
    """Single LLM call: structured_assessment → career recommendations."""

    @classmethod
    def generate(
        cls, *, structured_assessment: dict[str, Any]
    ) -> AIRecommendationPayload:
        prompt = build_recommendation_prompt()
        inputs = format_prompt_inputs(structured_assessment=structured_assessment)
        llm = get_chat_model()
        return cls._invoke_once(prompt=prompt, inputs=inputs, llm=llm)

    @classmethod
    def _invoke_once(cls, *, prompt, inputs: dict[str, Any], llm) -> AIRecommendationPayload:
        """Exactly one provider invocation (no retries, no fallback chain)."""
        try:
            structured_llm = llm.with_structured_output(
                AIRecommendationPayload,
                method="json_mode",
            )
            chain = prompt | structured_llm
            result = chain.invoke(inputs)
            raw = cls._coerce_payload(result)
            payload = normalize_payload(raw)
        except ValidationError as exc:
            logger.warning("LLM output validation failed: %s", exc)
            raise AIGenerationError("AI response failed validation") from exc
        except Exception as exc:
            logger.exception("LLM recommendation generation failed")
            raise AIGenerationError(_format_llm_error(exc)) from exc

        gaps = describe_shape_gaps(payload)
        if gaps:
            logger.warning("AI payload shape gaps after repair: %s", "; ".join(gaps))
            raise AIGenerationError(
                "AI response did not meet the required recommendation schema. "
                f"Details: {'; '.join(gaps)}"
            )
        return payload

    @staticmethod
    def _coerce_payload(result: Any) -> AIRecommendationPayload:
        payload = parse_ai_payload_lenient(result)
        if payload is not None:
            return payload
        return parse_ai_payload(result)


def _format_llm_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    if "429" in message:
        return "LLM rate limit reached. Retry in a few moments."
    return message
