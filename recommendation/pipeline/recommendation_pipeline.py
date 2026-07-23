from __future__ import annotations

import logging
from typing import Any, Callable

from ai.config import is_configured
from ai.provider import ensure_configured
from recommendation.config import ai_recommendations_enabled
from recommendation.exceptions import AIGenerationError, AIConfigurationError
from recommendation.generators.ai_recommendation_generator import (
    RecommendationGenerator,
)
from recommendation.schemas.recommendation_output import AIRecommendationPayload

logger = logging.getLogger(__name__)


class RecommendationPipeline:
    """structured_assessment -> single LLM call -> full AI recommendation JSON."""

    @classmethod
    def run(
        cls,
        *,
        structured_assessment: dict[str, Any],
        build_prompt: Callable,
        format_inputs: Callable,
    ) -> tuple[AIRecommendationPayload, int]:
        if not is_configured() or not ai_recommendations_enabled():
            raise AIConfigurationError("AI recommendations are temporarily unavailable")

        ensure_configured()
        try:
            return RecommendationGenerator.generate(
                structured_assessment=structured_assessment,
                build_prompt=build_prompt,
                format_inputs=format_inputs,
            )
        except AIGenerationError:
            raise
        except AIConfigurationError:
            raise
        except Exception as exc:
            logger.exception("Unexpected recommendation pipeline error")
            raise AIGenerationError(str(exc)) from exc
