from __future__ import annotations

import statistics
from typing import Any

from assessment.models import Question, StudentAssessment, UserResponse
from assessment.studentassessment import get_student_profile

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


class AssessmentContextBuilder:
    """Build compact assessment signals for AI prompts (no raw assessment JSON)."""

    @classmethod
    def build(cls, assessment: StudentAssessment) -> dict[str, Any]:
        profile = get_student_profile(assessment.user)
        dimension_scores = cls._dimension_scores(assessment)
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
        domain_category_name = getattr(assessment.domain_category, "domain_name", None)

        return {
            "assessment_id": assessment.id,
            "is_completed": assessment.is_completed,
            "education_level": education_level,
            "stream": stream_code,
            "domain": domain_name,
            "domain_category": domain_category_name,
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
    def _dimension_scores(cls, assessment: StudentAssessment) -> dict[str, float]:
        rows = (
            UserResponse.objects.filter(assessment=assessment)
            .select_related("question", "selected_option")
            .only(
                "id",
                "question__dimension",
                "selected_option__sequence_order",
            )
        )
        buckets: dict[str, list[float]] = {d.value: [] for d in DIMENSIONS}
        for row in rows:
            dim = (row.question.dimension or "").strip().lower()
            if dim not in buckets:
                continue
            buckets[dim].append(_option_score(row.selected_option.sequence_order))

        scores: dict[str, float] = {}
        for dim in buckets:
            values = buckets[dim]
            if values:
                scores[dim] = _normalize_score(statistics.mean(values))
            else:
                scores[dim] = 0.5
        return scores

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
