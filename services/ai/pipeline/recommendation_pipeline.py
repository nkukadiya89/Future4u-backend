from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from services.ai.clients.llm_client import ensure_ai_provider_configured
from services.ai.config import ai_llm_enabled
from services.ai.exceptions import AIGenerationError, AIConfigurationError
from services.ai.generators.ai_recommendation_generator import AIRecommendationGenerator
from services.ai.pipeline.output_normalizer import normalize_payload
from services.ai.schemas.recommendation_output import AIRecommendationPayload

logger = logging.getLogger(__name__)


class RecommendationPipeline:
    """student_signals + career_candidates → Groq → full recommendation JSON."""

    @classmethod
    def run(
        cls,
        *,
        student_signals: dict[str, Any],
        career_candidates: list[dict[str, Any]],
    ) -> AIRecommendationPayload:
        if not ai_llm_enabled():
            raise AIConfigurationError(
                "Groq is not configured. Set GROQ_API_KEY and AI_USE_OPENAI=true."
            )

        ensure_ai_provider_configured()
        try:
            raw = AIRecommendationGenerator.generate(
                student_signals=student_signals,
                career_candidates=career_candidates,
            )
            return normalize_payload(raw)
        except (ValidationError, AIGenerationError):
            raise
        except AIConfigurationError:
            raise
        except Exception as exc:
            logger.exception("Unexpected recommendation pipeline error")
            raise AIGenerationError(str(exc)) from exc
