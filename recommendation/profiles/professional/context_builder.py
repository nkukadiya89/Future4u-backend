from __future__ import annotations

from typing import Any

from assessment.models import ProfessionalAssessment
from recommendation.pipeline.assessment_ai_input_builder import build_ai_input


def get_professional_profile(user):
    try:
        from user_profile.models import ProfessionalProfile

        return ProfessionalProfile.objects.select_related(
            "education_level",
            "stream",
        ).get(user=user)
    except ProfessionalProfile.DoesNotExist:
        return None


class ProfessionalAssessmentContextBuilder:

    @classmethod
    def build_llm_input(cls, assessment: ProfessionalAssessment) -> dict[str, Any]:
        profile = get_professional_profile(assessment.user)
        education_level = None
        stream = None
        if profile:
            if profile.education_level_id:
                education_level = profile.education_level.display_name
            if profile.stream_id:
                stream = profile.stream.stream_name

        data = cls._assessment_data(assessment)

        structured = build_ai_input(
            {
                "education_level": education_level,
                "stream": stream,
                "domain_name": data.get("domain_name"),
                "domain_code": data.get("domain_code"),
                "domain_category_name": data.get("domain_category_name"),
                "responses": [],
                "career_direction": data.get("career_direction_name"),
                "parent_support": None,
                "concerns": data.get("guidance_reason_names"),
                "career_values": data.get("career_value_names"),
                "user_goals": data.get("platform_goal_names"),
            }
        )
        # Add professional-specific fields directly (build_ai_input ignores unknown keys)
        structured["career_intention"] = data.get("career_intention_display")
        structured["work_constraints"] = data.get("work_constraint_names")
        structured["preferred_environment"] = data.get("preferred_environment_display")
        structured["preferred_structure"] = data.get("preferred_structure_display")
        structured["salary_expectation"] = data.get("salary_expectation_display")
        structured["timeline"] = data.get("timeline_display")
        structured["employment_type"] = data.get("employment_type")
        structured["years_of_experience"] = data.get("years_of_experience")
        return structured

    @classmethod
    def _assessment_data(cls, assessment: ProfessionalAssessment) -> dict[str, Any]:
        """Collect assessment fields + lightweight profile fields only."""
        profile = get_professional_profile(assessment.user)

        return {
            # Assessment fields (display names for human-readable LLM input)
            "domain_name": (
                assessment.domain.domain_name
                if assessment.domain_id and assessment.domain
                else None
            ),
            "domain_code": (
                assessment.domain.domain_code
                if assessment.domain_id and assessment.domain
                else None
            ),
            "domain_category_name": (
                assessment.domain_category.domain_name
                if assessment.domain_category_id and assessment.domain_category
                else None
            ),
            "career_direction_name": [],
            "guidance_reason_names": (
                list(assessment.guidance_reasons.values_list("name", flat=True))
                if assessment.pk
                else []
            ),
            "work_constraint_names": (
                list(assessment.work_constraints.values_list("name", flat=True))
                if assessment.pk
                else []
            ),
            "career_value_names": (
                list(assessment.career_values.values_list("name", flat=True))
                if assessment.pk
                else []
            ),
            "platform_goal_names": (
                list(assessment.platform_goals.values_list("name", flat=True))
                if assessment.pk
                else []
            ),
            "career_intention_display": assessment.get_career_intention_display(),
            "preferred_environment_display": assessment.get_preferred_environment_display(),
            "preferred_structure_display": assessment.get_preferred_structure_display(),
            "salary_expectation_display": assessment.get_salary_expectation_display(),
            "timeline_display": assessment.get_timeline_display(),
            # Lightweight profile fields only (no JSON blobs)
            "employment_type": profile.employment_type if profile else None,
            "years_of_experience": profile.years_of_experience if profile else None,
        }
