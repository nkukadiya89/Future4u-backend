from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from services.ai.clients.openai_client import get_chat_model
from services.ai.exceptions import AIGenerationError
from services.ai.prompts.ai_recommendation_prompt import (
    build_recommendation_prompt,
    format_prompt_inputs,
)
from services.ai.schemas.recommendation_output import AIRecommendationPayload

logger = logging.getLogger(__name__)


class AIRecommendationGenerator:
    """LangChain structured-output generation for career recommendations."""

    @classmethod
    def generate(
        cls,
        *,
        student_signals: dict[str, Any],
        career_candidates: list[dict[str, Any]],
    ) -> AIRecommendationPayload:
        if not career_candidates:
            raise AIGenerationError(
                "No career candidates found for the selected domain"
            )

        prompt = build_recommendation_prompt()
        llm = get_chat_model()
        structured_llm = llm.with_structured_output(AIRecommendationPayload)
        chain = prompt | structured_llm

        try:
            result = chain.invoke(
                format_prompt_inputs(
                    student_signals=student_signals,
                    career_candidates=career_candidates,
                )
            )
        except ValidationError as exc:
            logger.warning("AI output validation failed during invoke: %s", exc)
            raise AIGenerationError("AI response failed validation") from exc
        except Exception as exc:
            logger.exception("OpenAI recommendation generation failed")
            message = str(exc).strip() or exc.__class__.__name__
            if "insufficient_quota" in message.lower():
                message = (
                    "OpenAI API quota exceeded. Add billing/credits at "
                    "https://platform.openai.com/account/billing"
                )
            elif "429" in message:
                message = "OpenAI rate limit reached. Retry in a few moments."
            raise AIGenerationError(message) from exc

        if isinstance(result, AIRecommendationPayload):
            payload = result
        else:
            try:
                payload = AIRecommendationPayload.model_validate(result)
            except ValidationError as exc:
                logger.warning("AI output validation failed: %s", exc)
                raise AIGenerationError("AI response failed validation") from exc

        if not cls._has_rich_shape(payload):
            raise AIGenerationError(
                "OpenAI response did not include the full recommendation schema. "
                "Retry the request."
            )
        return payload

    @staticmethod
    def _has_rich_shape(payload: AIRecommendationPayload) -> bool:
        if not payload.top_suggestions:
            return False
        first = payload.top_suggestions[0]
        roadmap = first.career_roadmap or {}
        factors = first.career_factors or {}
        education = first.required_education or {}
        return (
            "primary_degree" in education
            and "next_3_months" in roadmap
            and "salary" in factors
            and len(first.required_skills or []) >= 3
        )
