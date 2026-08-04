from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone

from assessment.models import (
    ParentAssessment,
    ProfessionalAssessment,
    StudentAssessment,
)
from project_recommendation.exceptions import ProjectRecommendationAccessDeniedError
from project_recommendation.models import ProjectRecommendation
from project_recommendation.services.project_generator import ProjectGenerator

# One AI generation per assessment, refreshed yearly from the project
# recommendation's OWN generation date (independent of any other feature).
PROJECT_RECOMMENDATION_CYCLE_DAYS = 365

# All assessment models that have domain + domain_category fields
_ASSESSMENT_MODELS: list[type[StudentAssessment | ParentAssessment | ProfessionalAssessment]] = [
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

        self._persist(
            user=user,
            assessment=assessment,
            domain=domain,
            domain_category=domain_category or domain,
            education_level=education_level,
            raw_response=data,
            token_usage=token_usage,
        )
        return response, token_usage

    @staticmethod
    def get_existing(
        user, assessment_id: int, cycle_days: int = PROJECT_RECOMMENDATION_CYCLE_DAYS
    ) -> dict[str, Any] | None:
        """Return the saved recommendation if still within the 365-day cycle.

        A second POST for the same assessment returns the persisted result
        without calling the LLM again (no token cost). The 365-day count
        starts from the project recommendation's OWN generation date
        (`last_recommended_at`) — fully independent of any other feature.
        When the cycle has expired, a fresh AI generation is allowed.
        """
        try:
            assessment = ProjectRecommendationService._resolve_assessment(
                user, assessment_id
            )
        except ProjectRecommendationAccessDeniedError:
            return None

        relation_kwargs = ProjectRecommendationService._assessment_relation_kwargs(
            assessment
        )
        record = (
            ProjectRecommendation.objects.filter(**relation_kwargs, deleted=False)
            .order_by("-last_recommended_at", "-id")
            .first()
        )
        if record is None:
            return None

        # 365-day count starts from the project recommendation's OWN generation
        # date — no other feature (e.g. career recommendation) is involved.
        anchor = record.last_recommended_at
        if anchor is None:
            return None  # no anchor -> allow a fresh AI generation

        next_allowed = anchor + timedelta(days=cycle_days)
        if timezone.now() >= next_allowed:
            return None  # expired cycle -> allow a fresh AI generation

        raw = record.raw_ai_response
        return {
            "domain": record.domain,
            "domain_category": record.domain_category,
            "assessment_id": assessment_id,
            "education_level": record.education_level,
            "projects": (
                raw.get("projects", []) if isinstance(raw, dict) else []
            ),
        }

    @staticmethod
    def _assessment_relation_kwargs(assessment) -> dict[str, Any]:
        """Return the profile_type + FK kwarg for the given assessment type."""
        if isinstance(assessment, StudentAssessment):
            return {
                "profile_type": ProjectRecommendation.ProfileType.STUDENT,
                "student_assessment": assessment,
            }
        if isinstance(assessment, ParentAssessment):
            return {
                "profile_type": ProjectRecommendation.ProfileType.PARENT,
                "parent_assessment": assessment,
            }
        return {
            "profile_type": ProjectRecommendation.ProfileType.PROFESSIONAL,
            "professional_assessment": assessment,
        }

    @staticmethod
    def _persist(
        *,
        user,
        assessment,
        domain: str,
        domain_category: str,
        education_level: str,
        raw_response: dict[str, Any],
        token_usage: int,
    ) -> ProjectRecommendation:
        """Upsert the full AI response — one row per assessment."""
        relation_kwargs = ProjectRecommendationService._assessment_relation_kwargs(
            assessment
        )
        now = timezone.now()

        existing = ProjectRecommendation.objects.filter(
            **relation_kwargs, deleted=False
        ).first()
        if existing:
            existing.domain = domain
            existing.domain_category = domain_category
            existing.education_level = education_level
            existing.raw_ai_response = raw_response
            existing.token_usage = token_usage
            existing.last_recommended_at = now
            existing._request_user = user
            existing.save(
                update_fields=[
                    "domain",
                    "domain_category",
                    "education_level",
                    "raw_ai_response",
                    "token_usage",
                    "last_recommended_at",
                    "updated_at",
                    "updated_by",
                ]
            )
            return existing

        record = ProjectRecommendation(
            user=user,
            **relation_kwargs,
            domain=domain,
            domain_category=domain_category,
            education_level=education_level,
            raw_ai_response=raw_response,
            token_usage=token_usage,
            last_recommended_at=now,
        )
        record._request_user = user
        record.save()
        return record

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
            profile = StudentProfile.objects.filter(user=user).select_related(
                "education_level"
            ).first()
            if profile and profile.education_level_id:
                return getattr(profile.education_level, "display_name", "") or ""

        elif isinstance(assessment, ParentAssessment):
            # Parent is assessing for a child — get child's education level
            from user_profile.models import ChildProfile
            child = ChildProfile.objects.select_related(
                "education_level"
            ).filter(
                id=assessment.child_id
            ).first()
            if child and child.education_level_id:
                return getattr(child.education_level, "display_name", "") or ""

        elif isinstance(assessment, ProfessionalAssessment):
            profile = ProfessionalProfile.objects.filter(user=user).select_related(
                "education_level"
            ).first()
            if profile and profile.education_level_id:
                return getattr(profile.education_level, "display_name", "") or ""

        return ""
