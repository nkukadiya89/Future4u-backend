from __future__ import annotations

import re
from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone

from assessment.models import Option, StudentAssessment, UserResponse
from assessment_career.models import CareerRecommendation, CareerRecommendationSuggestion
from recommendation.context.assessment_context_builder import AssessmentContextBuilder
from recommendation.exceptions import (
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from recommendation.pipeline.recommendation_pipeline import RecommendationPipeline

RECOMMENDATION_CYCLE_DAYS = 365
AI_RECOMMENDATION_DISCLAIMER = (
    "These AI recommendations are only guidance and do not guarantee any career, "
    "education, admission, job, or salary outcome. Please use them as a starting "
    "point and confirm important decisions with a qualified professional."
)
STUDY_ABROAD_SALARY_ABROAD_CLAUSE = (
    "abroad varies by country, visa status, degree level, and local demand"
)
STUDY_ABROAD_EXAM_CHECKS = (
    "IELTS/PTE/TOEFL",
    "GRE/GMAT if postgraduate/advanced",
    "German/French or other language requirements",
)
STUDY_ABROAD_ROADMAP_PHASES = (
    "next_3_months",
    "next_3_to_6_months",
    "next_6_to_9_months",
    "next_9_to_12_months",
)
STUDY_ABROAD_TEXT_REPLACEMENTS = (
    (
        re.compile(
            r"\b(?:IELTS|PTE|TOEFL)(?:\s*(?:/|,|\band\b|\bor\b)\s*(?:IELTS|PTE|TOEFL))*\b",
            re.IGNORECASE,
        ),
        "IELTS/PTE/TOEFL",
    ),
    (
        re.compile(
            r"\b(?:GRE|GMAT)(?:\s*(?:/|,|\band\b|\bor\b)\s*(?:GRE|GMAT))*\b",
            re.IGNORECASE,
        ),
        "GRE/GMAT",
    ),
    (
        re.compile(
            r"\b(?:SAT|ACT)(?:\s*(?:/|,|\band\b|\bor\b)\s*(?:SAT|ACT))*\b",
            re.IGNORECASE,
        ),
        "course-specific entrance tests",
    ),
)


def _is_study_abroad_assessment(structured_input: dict) -> bool:
    career_direction = structured_input.get("career_direction") or []
    if isinstance(career_direction, str):
        values = [career_direction]
    elif isinstance(career_direction, list):
        values = career_direction
    else:
        values = []
    return any(str(value).strip().casefold() == "study abroad" for value in values)


def _normalize_study_abroad_text(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for pattern, replacement in STUDY_ABROAD_TEXT_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text


def _normalize_study_abroad_salary_average(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return f"India: INR range varies by role; {STUDY_ABROAD_SALARY_ABROAD_CLAUSE}"

    india_part = text.split(";", 1)[0].strip()
    if not india_part.casefold().startswith("india:"):
        india_part = f"India: {india_part}"
    return f"{india_part}; {STUDY_ABROAD_SALARY_ABROAD_CLAUSE}"


def _normalize_study_abroad_exam_text(value: object) -> str:
    text = _normalize_study_abroad_text(value).rstrip(" .")
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


def _normalize_study_abroad_task_description(phase_name: str, value: object) -> str:
    if phase_name == "next_3_to_6_months":
        return _normalize_study_abroad_exam_text(value)
    return _normalize_study_abroad_text(value)


def _normalize_study_abroad_payload(payload):
    for suggestion in payload.top_suggestions:
        suggestion.ai_insight = _normalize_study_abroad_text(suggestion.ai_insight)
        suggestion.why_this_career = [
            _normalize_study_abroad_text(reason)
            for reason in suggestion.why_this_career
        ]
        suggestion.career_factors.salary.average = (
            _normalize_study_abroad_salary_average(
                suggestion.career_factors.salary.average
            )
        )
        roadmap = suggestion.career_roadmap
        for phase_name in STUDY_ABROAD_ROADMAP_PHASES:
            for task in getattr(roadmap, phase_name):
                task.task_description = _normalize_study_abroad_task_description(
                    phase_name,
                    task.task_description,
                )
    return payload


class AIRecommendationService:
    """Assessment signals -> Groq generates full recommendation JSON."""

    def generate(self, *, assessment_id: int, user) -> dict:
        assessment = self._load_assessment(assessment_id)
        if assessment.user_id != user.id:
            raise AssessmentAccessDeniedError("Assessment access denied")

        self._ensure_ready(assessment)

        # Check existing recommendation and 365-day cycle
        recommendation = CareerRecommendation.objects.filter(
            assessment=assessment, deleted=False
        ).prefetch_related("suggestions").first()

        if recommendation and recommendation.last_recommended_at:
            next_allowed = recommendation.last_recommended_at + timedelta(
                days=RECOMMENDATION_CYCLE_DAYS
            )
            if timezone.now() < next_allowed:
                # Within 365 days, return existing stored data.
                return self._serialize_recommendation(recommendation)

        # First time or 365 days passed: call AI with structured assessment signals.
        structured_input = AssessmentContextBuilder.build_llm_input(assessment)

        payload = RecommendationPipeline.run(structured_assessment=structured_input)
        if _is_study_abroad_assessment(structured_input):
            payload = _normalize_study_abroad_payload(payload)

        recommendation = self._save_recommendation(
            assessment,
            user,
            payload,
            recommendation,
        )
        return self._serialize_recommendation(recommendation)

    @staticmethod
    def _save_recommendation(assessment, user, payload, existing=None):
        now = timezone.now()
        payload_dict = payload.model_dump()

        if existing:
            existing.raw_ai_response = payload_dict
            existing.easy_decision_making = payload_dict.get("easy_decision_making", [])
            existing.last_recommended_at = now
            existing._request_user = user
            existing.save(
                update_fields=[
                    "raw_ai_response",
                    "easy_decision_making",
                    "last_recommended_at",
                    "updated_at",
                    "updated_by",
                ]
            )
            recommendation = existing
        else:
            recommendation = CareerRecommendation(
                user=user,
                assessment=assessment,
                raw_ai_response=payload_dict,
                easy_decision_making=payload_dict.get("easy_decision_making", []),
                last_recommended_at=now,
            )
            recommendation._request_user = user
            recommendation.save()

        # Replace suggestions
        existing_suggestions = list(
            recommendation.suggestions.filter(deleted=False).order_by("display_order")
        )
        for order, suggestion in enumerate(payload.top_suggestions, start=1):
            edu = (
                suggestion.required_education.model_dump()
                if suggestion.required_education
                else {}
            )
            factors = (
                suggestion.career_factors.model_dump()
                if suggestion.career_factors
                else {}
            )
            roadmap = suggestion.career_roadmap.model_dump()

            if order - 1 < len(existing_suggestions):
                # Update existing suggestion row
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
                        "career_name",
                        "match_percentage",
                        "ai_insight",
                        "why_this_career",
                        "required_skills",
                        "required_education",
                        "career_factors",
                        "career_roadmap",
                        "display_order",
                        "updated_at",
                        "updated_by",
                    ]
                )
            else:
                # Create if somehow fewer suggestions exist
                s = CareerRecommendationSuggestion(
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

        for stale_suggestion in existing_suggestions[len(payload.top_suggestions):]:
            stale_suggestion.soft_delete(user=user)

        return recommendation

    @staticmethod
    def _public_career_factors(factors):
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

    @staticmethod
    def _serialize_recommendation(recommendation):
        suggestions = []
        for s in recommendation.suggestions.filter(deleted=False).order_by(
            "display_order"
        ):
            career_factors = AIRecommendationService._public_career_factors(
                s.career_factors
            )
            suggestions.append(
                {
                    "id": s.id,
                    "recommendation": s.recommendation_id,
                    "career_name": s.career_name,
                    "match_percentage": s.match_percentage,
                    "ai_insight": s.ai_insight,
                    "why_this_career": s.why_this_career,
                    "required_skills": s.required_skills,
                    "required_education": (
                        {
                            "levels": (
                                (s.required_education or {}).get("levels", [])
                                if isinstance(s.required_education, dict)
                                else []
                            )
                        }
                        if s.required_education
                        else {"levels": []}
                    ),
                    "career_factors": career_factors,
                    "career_roadmap": s.career_roadmap,
                    "display_order": s.display_order,
                }
            )

        return {
            "ai_disclaimer": AI_RECOMMENDATION_DISCLAIMER,
            "top_suggestions": suggestions,
            "easy_decision_making": recommendation.easy_decision_making,
            "last_recommended_at": (
                recommendation.last_recommended_at.isoformat()
                if recommendation.last_recommended_at
                else None
            ),
        }

    @staticmethod
    def _load_assessment(assessment_id: int) -> StudentAssessment:
        response_qs = UserResponse.objects.select_related(
            "question",
            "selected_option",
        ).prefetch_related(
            Prefetch(
                "question__options",
                queryset=Option.objects.order_by("sequence_order"),
            )
        )
        try:
            return (
                StudentAssessment.objects.filter(deleted=False)
                .select_related(
                    "user",
                    "domain",
                    "domain_category",
                    "created_by",
                    "updated_by",
                    "deleted_by",
                )
                .prefetch_related(
                    Prefetch("responses", queryset=response_qs),
                    "career_direction",
                    "career_values",
                    "concerns",
                    "user_goals",
                )
                .get(id=assessment_id)
            )
        except StudentAssessment.DoesNotExist as exc:
            raise AssessmentNotFoundError("Assessment not found") from exc

    @staticmethod
    def _ensure_ready(assessment: StudentAssessment) -> None:
        if not assessment.domain_id:
            raise AssessmentNotReadyError(
                "Assessment domain is not set. Complete domain selection before AI recommendations."
            )
        has_responses = UserResponse.objects.filter(assessment=assessment).exists()
        has_profile_data = (
            assessment.career_direction.exists()
            or assessment.career_values.exists()
            or assessment.user_goals.exists()
            or assessment.concerns.exists()
            or bool(assessment.parent_support)
        )
        if not has_responses and not has_profile_data and not assessment.is_completed:
            raise AssessmentNotReadyError(
                "Insufficient assessment data. Answer questions or complete the assessment first."
            )
