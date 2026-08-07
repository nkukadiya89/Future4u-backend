"""Project recommendation service (AI only).

Generates 3 AI-powered portfolio project ideas via the LLM and persists
the result. Kept as ``ProjectRecommendationService`` with the same import
path and ``generate()`` signature as before, so existing callers (API
view, admin panel, tests) keep working without changes.
"""

from __future__ import annotations

from typing import Any

from project_recommendation.exceptions import ProjectRecommendationAccessDeniedError
from project_recommendation.services.ai_service import AIService


class ProjectRecommendationService:
    """AI-only project recommendation service."""

    def generate(
        self,
        *,
        user,
        domain: str,
        domain_category: str = "",
        overview: str = "",
    ) -> tuple[dict[str, Any], int]:
        domain = (domain or "").strip()
        domain_category = (domain_category or "").strip()
        if not domain:
            raise ProjectRecommendationAccessDeniedError(
                "Domain is required to generate project recommendations."
            )

        return AIService.generate(
            user=user,
            domain=domain,
            domain_category=domain_category,
            overview=overview,
        )

    @staticmethod
    def _profile_type_for_user(user) -> str:
        """Backward-compatible helper (delegates to the AI service)."""
        return AIService._profile_type_for_user(user)
