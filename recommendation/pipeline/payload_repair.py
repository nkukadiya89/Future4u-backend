from __future__ import annotations

from recommendation.config import (
    EASY_DECISION_CAREER_COUNT,
    EASY_DECISION_COUNT,
    TOP_SUGGESTION_COUNT,
)
from recommendation.schemas.recommendation_output import (
    AI_INSIGHT_MAX_WORDS,
    AI_INSIGHT_MIN_WORDS,
    AIRecommendationPayload,
    EasyDecisionItem,
    RequiredEducation,
    TopSuggestionItem,
    clip_ai_insight,
    clip_why_career_reason,
    normalize_education_suggestions,
)

_INSIGHT_PAD_WORDS = (
    "aligned",
    "with",
    "your",
    "assessment",
    "profile",
    "and",
    "career",
    "goals",
)

_WHY_PAD_WORDS = ("matches", "your", "profile", "well", "here")

_EASY_DECISION_TITLES = (
    "Best for quick start",
    "Best for high salary",
    "Best long term bet",
)


def ensure_ai_insight_word_band(text: str) -> str:
    """Groq often returns <14 words; expand then clip to schema band."""
    words = clip_ai_insight(text).split()
    if len(words) < AI_INSIGHT_MIN_WORDS:
        for word in _INSIGHT_PAD_WORDS:
            if len(words) >= AI_INSIGHT_MAX_WORDS:
                break
            words.append(word)
    return " ".join(words[:AI_INSIGHT_MAX_WORDS])


def ensure_why_bullet(text: str) -> str:
    clipped = clip_why_career_reason(text)
    words = clipped.split()
    from recommendation.schemas.recommendation_output import WHY_CAREER_MIN_WORDS

    if len(words) < WHY_CAREER_MIN_WORDS:
        for word in _WHY_PAD_WORDS:
            if len(words) >= WHY_CAREER_MIN_WORDS:
                break
            words.append(word)
    return clip_why_career_reason(" ".join(words))


def repair_required_education(
    education: RequiredEducation | None, *, career_name: str
) -> RequiredEducation:
    from recommendation.schemas.recommendation_output import EDUCATION_SUGGESTION_MIN

    if education and education.suggestions:
        suggestions = normalize_education_suggestions(list(education.suggestions))
    else:
        label = career_name.strip() or "this field"
        suggestions = [
            f"Bachelor's degree related to {label}",
            f"Industry certification for {label}",
        ]

    while len(suggestions) < EDUCATION_SUGGESTION_MIN:
        suggestions.append(suggestions[-1])
    return RequiredEducation(suggestions=suggestions[:3])


def repair_top_suggestion(item: TopSuggestionItem) -> TopSuggestionItem:
    why = [ensure_why_bullet(r) for r in item.why_this_career if str(r).strip()]
    if not why:
        why = [ensure_why_bullet(f"Strong fit for {item.career_name}")]

    return item.model_copy(
        update={
            "ai_insight": ensure_ai_insight_word_band(item.ai_insight),
            "why_this_career": why[:5],
            "required_education": repair_required_education(
                item.required_education,
                career_name=item.career_name,
            ),
        }
    )


def repair_easy_decision_making(
    payload: AIRecommendationPayload,
) -> list[EasyDecisionItem]:
    suggestions = payload.top_suggestions[:EASY_DECISION_CAREER_COUNT]
    if not suggestions:
        return list(payload.easy_decision_making)[:EASY_DECISION_COUNT]

    allowed = {s.career_name.strip().casefold() for s in suggestions}
    repaired: list[EasyDecisionItem] = []
    seen: set[tuple[str, str]] = set()

    for item in payload.easy_decision_making:
        key = item.career_name.strip().casefold()
        if key not in allowed:
            continue
        pair = (item.title.strip().casefold(), key)
        if pair in seen:
            continue
        seen.add(pair)
        repaired.append(item)

    compare_names = [s.career_name for s in suggestions]
    title_idx = 0
    while len(repaired) < EASY_DECISION_COUNT:
        career = compare_names[len(repaired) % len(compare_names)]
        title = _EASY_DECISION_TITLES[title_idx % len(_EASY_DECISION_TITLES)]
        title_idx += 1
        pair = (title.casefold(), career.strip().casefold())
        if pair in seen:
            continue
        seen.add(pair)
        repaired.append(EasyDecisionItem(title=title, career_name=career))

    return repaired[:EASY_DECISION_COUNT]


def repair_payload(payload: AIRecommendationPayload) -> AIRecommendationPayload:
    seen: set[str] = set()
    suggestions: list[TopSuggestionItem] = []

    for item in payload.top_suggestions:
        key = item.career_name.strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        suggestions.append(repair_top_suggestion(item))

    suggestions.sort(key=lambda s: s.match_percentage, reverse=True)
    suggestions = suggestions[:TOP_SUGGESTION_COUNT]

    interim = AIRecommendationPayload(
        top_suggestions=suggestions,
        easy_decision_making=payload.easy_decision_making,
    )
    easy = repair_easy_decision_making(interim)

    return AIRecommendationPayload(
        top_suggestions=suggestions,
        easy_decision_making=easy,
    )


def describe_shape_gaps(payload: AIRecommendationPayload) -> list[str]:
    """Human-readable gaps when counts are still insufficient after repair."""
    issues: list[str] = []
    if len(payload.top_suggestions) != TOP_SUGGESTION_COUNT:
        issues.append(
            f"expected {TOP_SUGGESTION_COUNT} top_suggestions, "
            f"got {len(payload.top_suggestions)}"
        )
    names = [s.career_name.strip().casefold() for s in payload.top_suggestions]
    if len(set(names)) != len(names):
        issues.append("duplicate career_name in top_suggestions")
    if len(payload.easy_decision_making) != EASY_DECISION_COUNT:
        issues.append(
            f"expected {EASY_DECISION_COUNT} easy_decision_making, "
            f"got {len(payload.easy_decision_making)}"
        )
    for item in payload.top_suggestions:
        roadmap = item.career_roadmap
        if not (
            roadmap.next_3_months
            and roadmap.next_3_to_6_months
            and roadmap.next_6_to_9_months
            and roadmap.next_9_to_12_months
        ):
            issues.append(f"missing roadmap phase for {item.career_name}")
    return issues
