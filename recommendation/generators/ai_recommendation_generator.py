from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from recommendation.config import EASY_DECISION_COUNT, TOP_SUGGESTION_COUNT
from recommendation.clients.llm_client import get_chat_model
from recommendation.exceptions import AIGenerationError
from recommendation.pipeline.output_normalizer import normalize_payload
from recommendation.pipeline.payload_validator import parse_ai_payload
from recommendation.prompts.ai_recommendation_prompt import (
    build_recommendation_prompt,
    format_prompt_inputs,
)
from recommendation.schemas.recommendation_output import AIRecommendationPayload

logger = logging.getLogger(__name__)


class AIRecommendationGenerator:
    """Single LLM call: structured_assessment -> career recommendations."""

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

        gaps = _payload_gaps(payload)
        if gaps:
            logger.warning("AI payload shape gaps: %s", "; ".join(gaps))
            raise AIGenerationError(
                "AI response did not meet the required recommendation schema. "
                f"Details: {'; '.join(gaps)}"
            )
        return payload

    @staticmethod
    def _coerce_payload(result: Any) -> AIRecommendationPayload:
        return parse_ai_payload(result)


def _format_llm_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    if "429" in message:
        return "LLM rate limit reached. Retry in a few moments."
    return message


def _payload_gaps(payload: AIRecommendationPayload) -> list[str]:
    issues: list[str] = []
    if len(payload.top_suggestions) != TOP_SUGGESTION_COUNT:
        issues.append(
            f"expected {TOP_SUGGESTION_COUNT} top_suggestions, "
            f"got {len(payload.top_suggestions)}"
        )
    names = [s.career_name.strip().casefold() for s in payload.top_suggestions]
    if len(set(names)) != len(names):
        issues.append("duplicate career_name in top_suggestions")
    if len(payload.easy_decision_making) != EASY_DECISION_COUNT:
        issues.append(
            f"expected {EASY_DECISION_COUNT} easy_decision_making, "
            f"got {len(payload.easy_decision_making)}"
        )
    for suggestion in payload.top_suggestions:
        name = suggestion.career_name
        factors = suggestion.career_factors
        if not factors.salary.average.strip():
            issues.append(f"missing salary.average for {name}")
        if not factors.salary.growth_rate.strip():
            issues.append(f"missing salary.growth_rate for {name}")
        if not factors.job_security.market_demand_growth.strip():
            issues.append(f"missing job_security.market_demand_growth for {name}")
        if "|" not in factors.job_security.market_demand_growth:
            issues.append(f"job_security.market_demand_growth must use 'X% | Y%' for {name}")
        if not factors.learning_curve.description.strip():
            issues.append(f"missing learning_curve.description for {name}")
    return issues
