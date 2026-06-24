from __future__ import annotations

from typing import Any

from assessment.models import ParentAssessment
from user_profile.models import ChildProfile


class ParentAssessmentContextBuilder:
    
    @classmethod
    def build_llm_input(cls, assessment: ParentAssessment) -> dict[str, Any]:
        data = cls._assessment_data(assessment)
        child = cls._get_child(assessment)

        return {
            "assessment_type": "parent",
            "domain_category": data.get("domain_category_name"),
            "career_direction": data.get("career_direction_name") or [],
            "parent_support": data.get("parent_support"),
            "concerns": data.get("concerns_name") or [],
            "parent_career_expectations": data.get("parent_career_expectations_name") or [],
            "limitations": data.get("limitations_name") or [],
            "career_familiarity": data.get("career_familiarity"),
            "decision_style": data.get("decision_style"),
            "career_values": data.get("career_values_name") or [],
            "user_goals": data.get("user_goals_name") or [],
            "child": {
                "first_name": child.first_name if child else None,
                "last_name": child.last_name if child else None,
                "education_level": child.education_level.display_name if child and child.education_level else None,
                "stream": child.stream.stream_name if child and child.stream else None,
                "academic_performance": child.academic_performance if child else None,
            } if child else None,
        }

    @classmethod
    def _assessment_data(cls, assessment: ParentAssessment) -> dict[str, Any]:
        return {
            "domain_category_name": (
                assessment.domain_category.domain_name
                if assessment.domain_category_id and assessment.domain_category
                else None
            ),
            "career_direction_name": (
                list(assessment.career_direction.values_list("name", flat=True))
                if assessment.pk
                else []
            ),
            "parent_support": assessment.parent_support,
            "concerns_name": (
                list(assessment.concerns.values_list("name", flat=True))
                if assessment.pk
                else []
            ),
            "parent_career_expectations_name": (
                list(assessment.parent_career_expectations.values_list("name", flat=True))
                if assessment.pk
                else []
            ),
            "limitations_name": (
                list(assessment.limitations.values_list("name", flat=True))
                if assessment.pk
                else []
            ),
            "career_familiarity": assessment.career_familiarity,
            "decision_style": assessment.decision_style,
            "career_values_name": (
                list(assessment.career_values.values_list("name", flat=True))
                if assessment.pk
                else []
            ),
            "user_goals_name": (
                list(assessment.user_goals.values_list("name", flat=True))
                if assessment.pk
                else []
            ),
        }

    @staticmethod
    def _get_child(assessment: ParentAssessment) -> ChildProfile | None:
        child = getattr(assessment, "child", None)
        if child and not child.deleted:
            return child
        return None
