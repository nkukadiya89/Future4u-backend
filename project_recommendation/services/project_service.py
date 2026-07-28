from __future__ import annotations

from typing import Any

from assessment_career.models import CareerRecommendation, CareerSuggestion
from project_recommendation.exceptions import ProjectRecommendationAccessDeniedError
from project_recommendation.schemas.project_output import ProjectRecommendationPayload
from project_recommendation.services.project_generator import ProjectGenerator


class ProjectRecommendationService:
    """Orchestrates AI personal project recommendation generation for students."""

    def generate(
        self,
        *,
        user,
        suggestion_id: int,
    ) -> tuple[dict[str, Any], int]:
        suggestion = self._load_suggestion(user=user, suggestion_id=suggestion_id)

        career_name = suggestion.career_name or ""
        match_percentage = suggestion.match_percentage
        required_skills = _format_skills(suggestion.required_skills)
        career_insight = suggestion.ai_insight or ""

        payload, token_usage = ProjectGenerator.generate(
            career_name=career_name,
            match_percentage=match_percentage,
            required_skills=required_skills,
            career_insight=career_insight,
        )
        return _build_response(payload, career_name, suggestion.id), token_usage

    def generate_batch(
        self,
        *,
        user,
        recommendation_id: int,
    ) -> tuple[dict[str, Any], int]:
        """
        Generate projects for ALL career suggestions in a recommendation.

        Returns a combined response with projects grouped by career.
        """
        recommendation = self._load_recommendation(
            user=user, recommendation_id=recommendation_id
        )

        suggestions = CareerSuggestion.objects.filter(
            recommendation=recommendation,
            deleted=False,
        ).order_by("display_order", "id")

        if not suggestions.exists():
            raise ProjectRecommendationAccessDeniedError(
                "No career suggestions found for this recommendation"
            )

        careers_data: list[dict[str, Any]] = []
        total_token_usage = 0

        for suggestion in suggestions:
            career_name = suggestion.career_name or ""
            match_percentage = suggestion.match_percentage
            required_skills = _format_skills(suggestion.required_skills)
            career_insight = suggestion.ai_insight or ""

            payload, token_usage = ProjectGenerator.generate(
                career_name=career_name,
                match_percentage=match_percentage,
                required_skills=required_skills,
                career_insight=career_insight,
            )
            total_token_usage += token_usage

            careers_data.append(
                _build_response(payload, career_name, suggestion.id)
            )

        return {
            "recommendation_id": recommendation.id,
            "careers": careers_data,
        }, total_token_usage

    @staticmethod
    def _load_suggestion(user, suggestion_id: int) -> CareerSuggestion:
        try:
            suggestion = CareerSuggestion.objects.select_related(
                "recommendation"
            ).get(
                id=suggestion_id,
                recommendation__user=user,
                recommendation__deleted=False,
                deleted=False,
            )
        except CareerSuggestion.DoesNotExist:
            raise ProjectRecommendationAccessDeniedError(
                "Career suggestion not found or access denied"
            )
        return suggestion

    @staticmethod
    def _load_recommendation(user, recommendation_id: int) -> CareerRecommendation:
        try:
            return CareerRecommendation.objects.get(
                id=recommendation_id,
                user=user,
                deleted=False,
            )
        except CareerRecommendation.DoesNotExist:
            raise ProjectRecommendationAccessDeniedError(
                "Career recommendation not found or access denied"
            )


def _format_skills(skills: Any) -> str:
    if not skills:
        return "Not specified"
    if isinstance(skills, list):
        return ", ".join(str(s) for s in skills if s)
    return str(skills)


def _build_response(
    payload: ProjectRecommendationPayload,
    career_name: str,
    suggestion_id: int,
) -> dict[str, Any]:
    projects_data = [project.model_dump() for project in payload.projects]
    return {
        "career": career_name,
        "suggestion_id": suggestion_id,
        "projects": projects_data,
    }

