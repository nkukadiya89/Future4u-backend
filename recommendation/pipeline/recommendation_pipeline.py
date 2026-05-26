from __future__ import annotations

import logging
from typing import Any

from recommendation.clients.llm_client import ensure_ai_provider_configured
from recommendation.config import ai_llm_enabled
from recommendation.exceptions import AIGenerationError, AIConfigurationError
from recommendation.generators.ai_recommendation_generator import AIRecommendationGenerator
from recommendation.schemas.recommendation_output import AIRecommendationPayload

logger = logging.getLogger(__name__)


class RecommendationPipeline:
    """structured_assessment -> single LLM call -> full AI recommendation JSON."""

    @classmethod
    def run(
        cls,
        *,
        structured_assessment: dict[str, Any],
    ) -> AIRecommendationPayload:
        if not ai_llm_enabled():
            raise AIConfigurationError(
                "AI recommendations are not configured. Set GROQ_API_KEY and AI_RECOMMENDATIONS_ENABLED=true."
            )

        ensure_ai_provider_configured()
        try:
            return AIRecommendationGenerator.generate(
                structured_assessment=structured_assessment,
            )
        except AIGenerationError:
            raise
        except AIConfigurationError:
            raise
        except Exception as exc:
            logger.exception("Unexpected recommendation pipeline error")
            raise AIGenerationError(str(exc)) from exc
