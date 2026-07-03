from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from recommendation.config import (
    STUDY_ABROAD_EXAM_CHECKS,
    STUDY_ABROAD_SALARY_CLAUSE,
    STUDY_ABROAD_TEXT_REPLACEMENTS,
)

logger = logging.getLogger(__name__)

RECOMMENDATION_CYCLE_DAYS = 365

AI_RECOMMENDATION_DISCLAIMER = (
    "These AI recommendations are only guidance and do not guarantee any career, "
    "education, admission, job, or salary outcome. Please use them as a starting "
    "point and confirm important decisions with a qualified professional."
)

# Study Abroad settings

STUDY_ABROAD_ROADMAP_PHASES = (
    "next_3_months",
    "next_3_to_6_months",
    "next_6_to_9_months",
    "next_9_to_12_months",
)

_STUDY_ABROAD_REPLACEMENTS = [
    (re.compile(item["exam_pattern"], re.IGNORECASE), item["normalized"])
    for item in STUDY_ABROAD_TEXT_REPLACEMENTS
]


def normalize_study_abroad_text(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for pattern, replacement in _STUDY_ABROAD_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text


def normalize_study_abroad_salary_average(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return f"India: INR range varies by role; {STUDY_ABROAD_SALARY_CLAUSE}"
    india_part = text.split(";", 1)[0].strip()
    if not india_part.casefold().startswith("india:"):
        india_part = f"India: {india_part}"
    return f"{india_part}; {STUDY_ABROAD_SALARY_CLAUSE}"


def normalize_study_abroad_exam_text(value: object) -> str:
    text = normalize_study_abroad_text(value).rstrip(" .")
    lowered = text.casefold()
    checks: list[str] = []
    if "ielts/pte/toefl" not in lowered:
        checks.append(STUDY_ABROAD_EXAM_CHECKS[0])
    if "gre/gmat" not in lowered:
        checks.append(STUDY_ABROAD_EXAM_CHECKS[1])
    has_language_requirement = (
        "german/french" in lowered
        or "other language requirement" in lowered
        or "country/course language" in lowered
    )
    if not has_language_requirement:
        checks.append(STUDY_ABROAD_EXAM_CHECKS[2])
    if not checks:
        return text
    if len(checks) > 2:
        checks_text = f"{', '.join(checks[:-1])}, and {checks[-1]}"
    elif len(checks) == 2:
        checks_text = f"{checks[0]} and {checks[1]}"
    else:
        checks_text = checks[0]
    return f"{text}. Check {checks_text}." if text else f"Check {checks_text}."


def normalize_study_abroad_task_description(phase_name: str, value: object) -> str:
    if phase_name == "next_3_to_6_months":
        return normalize_study_abroad_exam_text(value)
    return normalize_study_abroad_text(value)


def normalize_study_abroad_payload(payload):
    """Apply study-abroad text normalization to all suggestions in a payload."""
    for suggestion in payload.top_suggestions:
        suggestion.ai_insight = normalize_study_abroad_text(suggestion.ai_insight)
        suggestion.why_this_career = [
            normalize_study_abroad_text(reason) for reason in suggestion.why_this_career
        ]
        for level in suggestion.required_education.levels:
            level.name = normalize_study_abroad_text(level.name)
        suggestion.career_factors.salary.average = (
            normalize_study_abroad_salary_average(suggestion.career_factors.salary.average)
        )
        roadmap = suggestion.career_roadmap
        for phase_name in STUDY_ABROAD_ROADMAP_PHASES:
            for task in getattr(roadmap, phase_name):
                task.task_description = normalize_study_abroad_task_description(
                    phase_name, task.task_description,
                )
    return payload


# Shared helpers


def public_career_factors(factors: Any) -> Any:
    """Strip description from job_security for public API responses."""
    if not isinstance(factors, dict):
        return factors
    job_security = factors.get("job_security")
    if not isinstance(job_security, dict) or "description" not in job_security:
        return factors
    cleaned = dict(factors)
    cleaned["job_security"] = {
        key: value for key, value in job_security.items() if key != "description"
    }
    return cleaned


def _assessment_filter_kwargs(assessment):
    """Return the correct filter kwargs for the unified CareerRecommendation model."""
    from assessment.models import ProfessionalAssessment, StudentAssessment
    if isinstance(assessment, StudentAssessment):
        return {"student_assessment": assessment, "profile_type": "student"}
    if isinstance(assessment, ProfessionalAssessment):
        return {"professional_assessment": assessment, "profile_type": "working_professional"}
    return {"parent_assessment": assessment, "profile_type": "parent"}


def load_recommendation_and_check_cycle(
    *, assessment, recommendation_model, cycle_days: int = RECOMMENDATION_CYCLE_DAYS,
):
    """Return (recommendation, is_within_cycle)."""
    recommendation = recommendation_model.objects.filter(
        **_assessment_filter_kwargs(assessment), deleted=False
    ).prefetch_related("suggestions").first()

    if recommendation and recommendation.last_recommended_at:
        next_allowed = recommendation.last_recommended_at + timedelta(days=cycle_days)
        if timezone.now() < next_allowed:
            return recommendation, True
    return recommendation, False


@transaction.atomic
def save_recommendation(
    *, assessment, user, payload, recommendation_model, suggestion_model, existing=None,
):
    """Generic save/update for recommendations of any profile type.
    
    The `payload` must have `.model_dump()`, `.top_suggestions` (iterable).
    Each suggestion must have .career_name, .match_percentage, .ai_insight,
    .why_this_career, .required_skills, .required_education, .career_factors, .career_roadmap.
    """
    now = timezone.now()
    payload_dict = payload.model_dump()

    if existing:
        existing.raw_ai_response = payload_dict
        existing.easy_decision_making = payload_dict.get("easy_decision_making", [])
        existing.last_recommended_at = now
        existing._request_user = user
        existing.save(
            update_fields=[
                "raw_ai_response", "easy_decision_making",
                "last_recommended_at", "updated_at", "updated_by",
            ]
        )
        recommendation = existing
    else:
        fk_field = _assessment_filter_kwargs(assessment)
        recommendation = recommendation_model(
            user=user,
            **fk_field,
            raw_ai_response=payload_dict,
            easy_decision_making=payload_dict.get("easy_decision_making", []),
            last_recommended_at=now,
        )
        recommendation._request_user = user
        recommendation.save()

    existing_suggestions = list(
        recommendation.suggestions.filter(deleted=False).order_by("display_order")
    )

    for order, suggestion in enumerate(payload.top_suggestions, start=1):
        edu = (
            suggestion.required_education.model_dump()
            if suggestion.required_education else {}
        )
        factors = (
            suggestion.career_factors.model_dump()
            if suggestion.career_factors else {}
        )
        roadmap = suggestion.career_roadmap.model_dump()

        if order - 1 < len(existing_suggestions):
            s = existing_suggestions[order - 1]
            s.career_name = suggestion.career_name
            s.match_percentage = suggestion.match_percentage
            s.ai_insight = suggestion.ai_insight
            s.why_this_career = suggestion.why_this_career
            s.required_skills = suggestion.required_skills
            s.required_education = edu
            s.career_factors = factors
            s.career_roadmap = roadmap
            s.display_order = order
            s._request_user = user
            s.save(
                update_fields=[
                    "career_name", "match_percentage", "ai_insight",
                    "why_this_career", "required_skills", "required_education",
                    "career_factors", "career_roadmap", "display_order",
                    "updated_at", "updated_by",
                ]
            )
        else:
            s = suggestion_model(
                recommendation=recommendation,
                career_name=suggestion.career_name,
                match_percentage=suggestion.match_percentage,
                ai_insight=suggestion.ai_insight,
                why_this_career=suggestion.why_this_career,
                required_skills=suggestion.required_skills,
                required_education=edu,
                career_factors=factors,
                career_roadmap=roadmap,
                display_order=order,
            )
            s._request_user = user
            s.save()

    for stale in existing_suggestions[len(payload.top_suggestions):]:
        stale.soft_delete(user=user)

    return recommendation


def serialize_recommendation(recommendation):
    """Generic serialization for any recommendation type.
    
    Assumes recommendation.suggestions (filtered, ordered by display_order)
    with fields: id, career_name, match_percentage, ai_insight, why_this_career,
    required_skills, required_education, career_factors, career_roadmap, display_order.
    """
    suggestions = []
    for s in recommendation.suggestions.filter(deleted=False).order_by("display_order"):
        suggestions.append({
            "id": s.id,
            "recommendation": s.recommendation_id,
            "career_name": s.career_name,
            "match_percentage": s.match_percentage,
            "ai_insight": s.ai_insight,
            "why_this_career": s.why_this_career,
            "required_skills": s.required_skills,
            "required_education": (
                {"levels": (s.required_education or {}).get("levels", [])}
                if s.required_education else {"levels": []}
            ),
            "career_factors": public_career_factors(s.career_factors),
            "career_roadmap": s.career_roadmap,
            "display_order": s.display_order,
        })

    return {
        "ai_disclaimer": AI_RECOMMENDATION_DISCLAIMER,
        "top_suggestions": suggestions,
        "easy_decision_making": recommendation.easy_decision_making,
        "last_recommended_at": (
            recommendation.last_recommended_at.isoformat()
            if recommendation.last_recommended_at else None
        ),
    }
