"""AI-mode implementation: LLM-generated project recommendations.

Contains the exact logic that previously lived in
``ProjectRecommendationService.generate`` — nothing about the AI flow
has changed, it is only relocated behind a dedicated service class.
"""

from __future__ import annotations

from typing import Any

from project_recommendation.exceptions import ProjectRecommendationAccessDeniedError
from project_recommendation.services.persistence import (
    persist_recommendation,
    profile_type_for_user,
)
from project_recommendation.services.project_generator import ProjectGenerator


class AIService:
    """Generates 3 AI-powered portfolio project ideas via the LLM."""

    @classmethod
    def generate(
        cls,
        *,
        user,
        domain: str,
        domain_category: str = "",
        overview: str = "",
    ) -> tuple[dict[str, Any], int]:
        """Run the LLM and persist the result. Returns (response, token_usage)."""
        domain = (domain or "").strip()
        domain_category = (domain_category or "").strip()
        if not domain:
            raise ProjectRecommendationAccessDeniedError(
                "Domain is required to generate project recommendations."
            )

        payload, token_usage = ProjectGenerator.generate(
            domain=domain,
            domain_category=domain_category or domain,
            career_name=domain,
            overview=overview,
        )

        data = payload.model_dump()
        response = {
            "domain": domain,
            "domain_category": domain_category or domain,
            "overview": overview,
            "projects": data.get("projects", []),
        }

        persist_recommendation(
            user=user,
            domain=domain,
            domain_category=domain_category or domain,
            overview=overview,
            raw_response=data,
            token_usage=token_usage,
        )
        return response, token_usage

    @staticmethod
    def _profile_type_for_user(user) -> str:
        """Backward-compatible helper (delegates to the shared helper)."""
        return profile_type_for_user(user)
