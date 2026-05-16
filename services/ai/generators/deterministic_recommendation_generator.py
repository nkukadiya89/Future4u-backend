from __future__ import annotations

from typing import Any

from services.ai.context.recommendation_response_builder import RecommendationResponseBuilder
from services.ai.schemas.recommendation_output import AIRecommendationPayload


class DeterministicRecommendationGenerator:
    """Build rich frontend-ready recommendations from PostgreSQL data."""

    @classmethod
    def generate(
        cls,
        *,
        student_signals: dict[str, Any],
        career_candidates: list[dict[str, Any]],
    ) -> AIRecommendationPayload:
        return RecommendationResponseBuilder.build(
            student_signals=student_signals,
            career_candidates=career_candidates,
        )
