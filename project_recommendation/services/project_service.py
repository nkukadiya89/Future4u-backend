from __future__ import annotations

from typing import Any

from assessment.models import (
    ParentAssessment,
    ProfessionalAssessment,
    StudentAssessment,
)
from project_recommendation.exceptions import ProjectRecommendationAccessDeniedError
from project_recommendation.services.project_generator import ProjectGenerator

# All assessment models that have domain + domain_category fields
_ASSESSMENT_MODELS: list[
    type[StudentAssessment | ParentAssessment | ProfessionalAssessment]
] = [
    StudentAssessment,
    ParentAssessment,
    ProfessionalAssessment,
]


class ProjectRecommendationService:
    """Orchestrates AI portfolio project generation from an assessment."""

    def generate(
        self,
        *,
        user,
        assessment_id: int,
    ) -> tuple[dict[str, Any], int]:
        assessment = self._resolve_assessment(user, assessment_id)

        # Extract domain names from the Domain FK objects
        domain = ""
        domain_category = ""
        career_name = ""

        if assessment.domain_id:
            domain = getattr(assessment.domain, "domain_name", "") or ""
        if assessment.domain_category_id:
            domain_category = (
                getattr(assessment.domain_category, "domain_name", "") or ""
            )

        if not domain:
            raise ProjectRecommendationAccessDeniedError(
                "Assessment has no domain selected. Please complete the assessment first."
            )

        career_name = domain

        # Resolve education level based on assessment type
        education_level = self._resolve_education_level(user, assessment)

        payload, token_usage = ProjectGenerator.generate(
            domain=domain,
            domain_category=domain_category or domain,
            career_name=career_name,
            education_level=education_level,
        )

        data = payload.model_dump()
        response = {
            "domain": domain,
            "domain_category": domain_category or domain,
            "assessment_id": assessment_id,
            "education_level": education_level,
            "projects": data.get("projects", []),
        }
        return response, token_usage

    @staticmethod
    def _resolve_assessment(user, assessment_id: int):
        """Try all assessment types to find the assessment by ID + user."""
        for ModelClass in _ASSESSMENT_MODELS:
            try:
                assessment = ModelClass.objects.select_related(
                    "domain", "domain_category"
                ).get(
                    id=assessment_id,
                    user=user,
                    deleted=False,
                )
                return assessment
            except ModelClass.DoesNotExist:
                continue

        raise ProjectRecommendationAccessDeniedError(
            "Assessment not found or access denied"
        )

    @staticmethod
    def _resolve_education_level(user, assessment) -> str:
        """Get the user's education level based on assessment type."""
        from user_profile.models import StudentProfile, ProfessionalProfile

        if isinstance(assessment, StudentAssessment):
            profile = (
                StudentProfile.objects.filter(user=user)
                .select_related("education_level")
                .first()
            )
            if profile and profile.education_level_id:
                return getattr(profile.education_level, "display_name", "") or ""

        elif isinstance(assessment, ParentAssessment):
            # Parent is assessing for a child — get child's education level
            from user_profile.models import ChildProfile

            child = (
                ChildProfile.objects.select_related("education_level")
                .filter(id=assessment.child_id)
                .first()
            )
            if child and child.education_level_id:
                return getattr(child.education_level, "display_name", "") or ""

        elif isinstance(assessment, ProfessionalAssessment):
            profile = (
                ProfessionalProfile.objects.filter(user=user)
                .select_related("education_level")
                .first()
            )
            if profile and profile.education_level_id:
                return getattr(profile.education_level, "display_name", "") or ""

        return ""
