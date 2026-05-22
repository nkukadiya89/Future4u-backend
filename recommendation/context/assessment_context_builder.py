from __future__ import annotations

import statistics
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from assessment.models import Question, StudentAssessment, UserResponse
from assessment.serializers import StudentAssessmentSerializer
from assessment.studentassessment import get_student_profile
from recommendation.pipeline.assessment_scoring import build_ai_input, calculate_dimension_scores

DIMENSIONS = (
    Question.Dimension.INTEREST,
    Question.Dimension.APTITUDE,
    Question.Dimension.PERSONALITY,
    Question.Dimension.WORK_STYLE,
)


def _level_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "moderate"
    return "developing"


def _option_score(sequence_order: int) -> float:
    """Map option order to a 1–5 agreement scale."""
    return float(max(1, min(5, int(sequence_order or 1))))


def _normalize_score(raw: float) -> float:
    return round(max(0.0, min(1.0, (raw - 1.0) / 4.0)), 2)


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
    """Build assessment context for APIs and structured LLM input."""

    @classmethod
    def build(cls, assessment: StudentAssessment) -> dict[str, Any]:
        payload = cls.serialize_assessment_api(assessment)
        payload["computed_signals"] = cls.build_computed_signals(assessment)
        return _make_json_safe(payload)

    @classmethod
    def build_llm_input(cls, assessment: StudentAssessment) -> dict[str, Any]:
        """
        LLM payload: MCQ responses → dimension_scores; profile fields unchanged.
        Same source as GET /api/student/assessments/{id}/ but without raw Q&A.
        """
        api = cls.serialize_assessment_api(assessment)
        structured = build_ai_input(
            {
                "domain_name": api.get("domain_name"),
                "domain_category_name": api.get("domain_category_name"),
                "responses": api.get("responses") or [],
                "career_direction": api.get("career_direction"),
                "parent_support": api.get("parent_support"),
                "concerns": api.get("concerns"),
                "career_values": api.get("career_values"),
                "user_goals": api.get("user_goals"),
                "is_completed": api.get("is_completed"),
            }
        )
        return _make_json_safe(structured)

    @classmethod
    def serialize_assessment_api(cls, assessment: StudentAssessment) -> dict[str, Any]:
        """Same shape as GET /api/student/assessments/{id}/ (JSON-safe values)."""
        serializer = StudentAssessmentSerializer(assessment)
        return _make_json_safe(dict(serializer.data))

    @classmethod
    def build_computed_signals(cls, assessment: StudentAssessment) -> dict[str, Any]:
        profile = get_student_profile(assessment.user)
        response_dicts = cls._responses_as_dicts(assessment)
        dimension_scores = calculate_dimension_scores(response_dicts)
        consistency = cls._response_consistency(assessment)
        traits = cls._derive_traits(dimension_scores)
        support = cls._support_system_label(assessment.parent_support)

        education_level = None
        stream_code = None
        if profile:
            if profile.education_level_id:
                education_level = profile.education_level.level_code
            if profile.stream_id:
                stream_code = profile.stream.stream_code

        domain_name = getattr(assessment.domain, "domain_name", None)
        domain_code = getattr(assessment.domain, "domain_code", None)
        domain_category_name = getattr(assessment.domain_category, "domain_name", None)
        domain_category_code = getattr(assessment.domain_category, "domain_code", None)

        profile_block: dict[str, Any] = {}
        if profile:
            profile_block = {
                "education_level": education_level,
                "education_level_name": (
                    profile.education_level.display_name
                    if profile.education_level_id
                    else None
                ),
                "stream": stream_code,
                "stream_name": (
                    profile.stream.stream_name if profile.stream_id else None
                ),
            }

        return {
            "assessment_id": assessment.id,
            "is_completed": assessment.is_completed,
            "user_profile": profile_block,
            "education_level": education_level,
            "stream": stream_code,
            "domain": domain_name,
            "domain_code": domain_code,
            "domain_category": domain_category_name,
            "domain_category_code": domain_category_code,
            "career_direction": cls._compact_list(assessment.career_direction),
            "career_values": cls._compact_list(assessment.career_values),
            "concerns": cls._compact_list(assessment.concerns),
            "user_goals": cls._compact_list(assessment.user_goals),
            "parent_support": assessment.parent_support,
            "dimension_scores": dimension_scores,
            "personality_traits": traits["personality_traits"],
            "creativity": traits["creativity"],
            "analytical_ability": traits["analytical_ability"],
            "communication_style": traits["communication_style"],
            "work_style": traits["work_style"],
            "strengths": traits["strengths"],
            "ambition": traits["ambition"],
            "consistency": consistency,
            "support_system": support,
        }

    @classmethod
    def _responses_as_dicts(cls, assessment: StudentAssessment) -> list[dict[str, Any]]:
        rows = (
            UserResponse.objects.filter(assessment=assessment)
            .select_related("question", "selected_option")
            .only(
                "id",
                "question__dimension",
                "selected_option__sequence_order",
            )
        )
        return [
            {
                "question": {"dimension": row.question.dimension},
                "selected_option": {
                    "sequence_order": row.selected_option.sequence_order,
                },
            }
            for row in rows
        ]

    @classmethod
    def _dimension_scores(cls, assessment: StudentAssessment) -> dict[str, float]:
        return calculate_dimension_scores(cls._responses_as_dicts(assessment))

    @classmethod
    def _response_consistency(cls, assessment: StudentAssessment) -> str:
        values = list(
            UserResponse.objects.filter(assessment=assessment)
            .select_related("selected_option")
            .values_list("selected_option__sequence_order", flat=True)
        )
        if len(values) < 2:
            return "limited_data"
        try:
            spread = statistics.pstdev([_option_score(v) for v in values])
        except statistics.StatisticsError:
            return "moderate"
        if spread <= 0.8:
            return "high"
        if spread <= 1.4:
            return "moderate"
        return "variable"

    @classmethod
    def _derive_traits(cls, scores: dict[str, float]) -> dict[str, Any]:
        interest = scores.get("interest", 0.5)
        aptitude = scores.get("aptitude", 0.5)
        personality = scores.get("personality", 0.5)
        work_style = scores.get("work_style", 0.5)

        personality_traits: list[str] = []
        if personality >= 0.65:
            personality_traits.extend(["collaborative", "empathetic"])
        elif personality <= 0.4:
            personality_traits.extend(["reserved", "independent"])
        else:
            personality_traits.append("balanced")

        if interest >= 0.65:
            personality_traits.append("curious")
        if aptitude >= 0.65:
            personality_traits.append("logical")

        communication = (
            "expressive and people-oriented"
            if personality >= 0.6
            else "thoughtful and precise"
            if aptitude >= 0.6
            else "balanced communicator"
        )

        work_style_label = (
            "structured and process-driven"
            if work_style >= 0.65
            else "flexible and adaptive"
            if work_style <= 0.4
            else "balanced work approach"
        )

        strengths: list[str] = []
        for label, key in (
            ("creative thinking", "interest"),
            ("analytical problem solving", "aptitude"),
            ("interpersonal awareness", "personality"),
            ("execution discipline", "work_style"),
        ):
            if scores.get(key, 0.5) >= 0.6:
                strengths.append(label)
        if not strengths:
            strengths.append("well-rounded potential")

        ambition = (
            "high growth orientation"
            if max(interest, aptitude) >= 0.7
            else "steady progress orientation"
        )

        return {
            "personality_traits": personality_traits[:6],
            "creativity": _level_label(interest),
            "analytical_ability": _level_label(aptitude),
            "communication_style": communication,
            "work_style": work_style_label,
            "strengths": strengths[:5],
            "ambition": ambition,
        }

    @staticmethod
    def _support_system_label(parent_support: str | None) -> str:
        mapping = {
            "very_supportive": "strong family support",
            "somewhat_supportive": "moderate family support",
            "neutral": "neutral family support",
            "not_supportive": "limited family support",
            "notsure": "uncertain family support",
        }
        return mapping.get(parent_support or "", "support level not specified")

    @staticmethod
    def _compact_list(value) -> list[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()][:8]
        text = str(value).strip()
        return [text] if text else []
