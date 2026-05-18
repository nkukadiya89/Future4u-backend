from __future__ import annotations

from services.ai.config import TOP_SUGGESTION_COUNT
from services.ai.pipeline.roadmap_normalizer import normalize_career_roadmap
from services.ai.schemas.recommendation_output import (
    AIRecommendationPayload,
    CareerRoadmap,
    EasyDecisionItem,
    TopSuggestionItem,
)


def _clamp_match(value: int) -> int:
    return max(0, min(100, int(value)))


def normalize_payload(payload: AIRecommendationPayload) -> AIRecommendationPayload:
    seen_names: set[str] = set()
    suggestions: list[TopSuggestionItem] = []

    for item in payload.top_suggestions:
        key = item.career_name.strip().casefold()
        if not key or key in seen_names:
            continue
        seen_names.add(key)

        roadmap_dict = normalize_career_roadmap(item.career_roadmap.model_dump())
        suggestions.append(
            item.model_copy(
                update={
                    "match_percentage": _clamp_match(item.match_percentage),
                    "required_skills": item.required_skills[:8],
                    "why_this_career": item.why_this_career[:5],
                    "career_roadmap": CareerRoadmap.model_validate(roadmap_dict),
                }
            )
        )

    suggestions.sort(key=lambda s: s.match_percentage, reverse=True)
    suggestions = suggestions[:TOP_SUGGESTION_COUNT]

    allowed = {s.career_name.strip().casefold() for s in suggestions}
    easy = [
        d
        for d in payload.easy_decision_making
        if d.career_name.strip().casefold() in allowed
    ][:TOP_SUGGESTION_COUNT]

    if len(easy) < TOP_SUGGESTION_COUNT and suggestions:
        existing = {e.career_name.strip().casefold() for e in easy}
        for s in suggestions:
            key = s.career_name.strip().casefold()
            if key in existing:
                continue
            easy.append(
                EasyDecisionItem(
                    title=f"Consider {s.career_name}",
                    career_name=s.career_name,
                    reason=s.ai_insight[:500],
                )
            )
            existing.add(key)
            if len(easy) >= TOP_SUGGESTION_COUNT:
                break

    return AIRecommendationPayload(
        top_suggestions=suggestions,
        easy_decision_making=easy[:TOP_SUGGESTION_COUNT],
    )
