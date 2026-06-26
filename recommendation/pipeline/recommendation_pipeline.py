from __future__ import annotations

import logging
from typing import Any, Callable

from recommendation.clients.llm_client import ensure_ai_provider_configured
from recommendation.config import ai_llm_enabled
from recommendation.exceptions import AIGenerationError, AIConfigurationError
from recommendation.generators.ai_recommendation_generator import RecommendationGenerator
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
    ) -> AIRecommendationPayload:
        if not ai_llm_enabled():
            raise AIConfigurationError(
                "AI recommendations are temporarily unavailable"
            )

        ensure_ai_provider_configured()
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
