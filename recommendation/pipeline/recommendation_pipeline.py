from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from recommendation.clients.llm_client import ensure_ai_provider_configured
from recommendation.config import EASY_DECISION_COUNT, TOP_SUGGESTION_COUNT, ai_llm_enabled
from recommendation.exceptions import AIGenerationError, AIConfigurationError
from recommendation.generators.ai_recommendation_generator import AIRecommendationGenerator
from recommendation.schemas.recommendation_output import AIRecommendationPayload

logger = logging.getLogger(__name__)


class RecommendationPipeline:
    """structured_assessment → single LLM call → full AI recommendation JSON."""

    @classmethod
    def run(
        cls,
        *,
        structured_assessment: dict[str, Any],
    ) -> AIRecommendationPayload:
        if not ai_llm_enabled():
            raise AIConfigurationError(
                "Groq is not configured. Set GROQ_API_KEY and AI_USE_OPENAI=true."
            )

        ensure_ai_provider_configured()
        try:
            normalized = AIRecommendationGenerator.generate(
                structured_assessment=structured_assessment,
            )
            if len(normalized.top_suggestions) != TOP_SUGGESTION_COUNT:
                raise AIGenerationError(
                    "AI recommendations must include 3 unique careers."
                )
            names = [
                s.career_name.strip().casefold() for s in normalized.top_suggestions
            ]
            if len(set(names)) != TOP_SUGGESTION_COUNT:
                raise AIGenerationError(
                    "AI recommendations must not repeat the same career_name."
                )
            if len(normalized.easy_decision_making) < EASY_DECISION_COUNT:
                raise AIGenerationError(
                    "AI recommendations missing easy decision cards."
                )
            return normalized
        except (ValidationError, AIGenerationError):
            raise
        except AIConfigurationError:
            raise
        except Exception as exc:
            logger.exception("Unexpected recommendation pipeline error")
            raise AIGenerationError(str(exc)) from exc
