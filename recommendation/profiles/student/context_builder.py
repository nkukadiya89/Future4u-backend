from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from assessment.models import StudentAssessment
from assessment.serializers import StudentAssessmentSerializer
from assessment.studentassessment import get_student_profile
from recommendation.pipeline.assessment_ai_input_builder import build_ai_input


def _make_json_safe(value: Any) -> Any:
    """Recursively convert UUID/datetime values for json.dumps."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_json_safe(item) for item in value]
    return str(value)


class AssessmentContextBuilder:
    """Build structured LLM input from an assessment."""

    @classmethod
    def build_llm_input(cls, assessment: StudentAssessment) -> dict[str, Any]:
        """
        LLM payload: selected answer signals and profile labels.
        Uses the same serializer as GET /api/student/assessments/{id}/ (*_name fields).
        """
        api = cls._assessment_data(assessment)
        profile = get_student_profile(assessment.user)
        education_level = None
        stream = None
        if profile:
            if profile.education_level_id:
                education_level = profile.education_level.display_name
            if profile.stream_id:
                stream = profile.stream.stream_name

        structured = build_ai_input(
            {
                "education_level": education_level,
                "stream": stream,
                "domain_name": api.get("domain_name")
                or getattr(assessment.domain, "domain_name", None),
                "domain_code": api.get("domain_code")
                or getattr(assessment.domain, "domain_code", None),
                "domain_category_name": api.get("domain_category_name")
                or getattr(assessment.domain_category, "domain_name", None),
                "responses": api.get("responses") or [],
                "career_direction": api.get("career_direction_name"),
                "parent_support": api.get("parent_support"),
                "concerns": api.get("concerns_name"),
                "career_values": api.get("career_values_name"),
                "user_goals": api.get("user_goals_name"),
            }
        )
        return _make_json_safe(structured)

    @classmethod
    def _assessment_data(cls, assessment: StudentAssessment) -> dict[str, Any]:
        """Same shape as GET /api/student/assessments/{id}/ (JSON-safe values)."""
        serializer = StudentAssessmentSerializer(assessment)
        return _make_json_safe(dict(serializer.data))
