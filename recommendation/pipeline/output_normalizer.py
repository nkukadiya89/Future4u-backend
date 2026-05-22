from __future__ import annotations

from recommendation.config import (
    EASY_DECISION_CAREER_COUNT,
    EASY_DECISION_COUNT,
    TOP_SUGGESTION_COUNT,
)
from recommendation.pipeline.payload_repair import repair_easy_decision_making, repair_payload
from recommendation.pipeline.roadmap_normalizer import normalize_career_roadmap
from recommendation.schemas.recommendation_output import (
    AIRecommendationPayload,
    CareerRoadmap,
    RequiredEducation,
    TopSuggestionItem,
    clip_ai_insight,
    clip_why_career_reason,
    normalize_education_suggestions,
)


def _clamp_match(value: int) -> int:
    return max(0, min(100, int(value)))


def normalize_payload(payload: AIRecommendationPayload) -> AIRecommendationPayload:
    """Repair, clip, and order AI output (no DB template injection)."""
    payload = repair_payload(payload)

    seen_names: set[str] = set()
    suggestions: list[TopSuggestionItem] = []

    for item in payload.top_suggestions:
        key = item.career_name.strip().casefold()
        if not key or key in seen_names:
            continue
        seen_names.add(key)

        roadmap_dict = normalize_career_roadmap(item.career_roadmap.model_dump())
        why_this_career = [
            clip_why_career_reason(r)
            for r in item.why_this_career[:5]
            if str(r).strip()
        ]
        required_skills = item.required_skills[:8]

        education: RequiredEducation | None = item.required_education
        if education:
            suggestions_edu = normalize_education_suggestions(education.suggestions)
            if suggestions_edu:
                education = RequiredEducation(suggestions=suggestions_edu)

        suggestions.append(
            item.model_copy(
                update={
                    "match_percentage": _clamp_match(item.match_percentage),
                    "ai_insight": clip_ai_insight(item.ai_insight),
                    "required_skills": required_skills,
                    "required_education": education,
                    "why_this_career": why_this_career,
                    "career_roadmap": CareerRoadmap.model_validate(roadmap_dict),
                }
            )
        )

    suggestions.sort(key=lambda s: s.match_percentage, reverse=True)
    suggestions = suggestions[:TOP_SUGGESTION_COUNT]

    interim = AIRecommendationPayload(
        top_suggestions=suggestions,
        easy_decision_making=payload.easy_decision_making,
    )
    easy = repair_easy_decision_making(interim)[:EASY_DECISION_COUNT]

    return AIRecommendationPayload(
        top_suggestions=suggestions,
        easy_decision_making=easy,
    )
