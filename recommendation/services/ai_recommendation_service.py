from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

RECOMMENDATION_CYCLE_DAYS = 365


class AIRecommendationService:
    """Assessment signals → Groq generates full recommendation JSON (all careers from LLM)."""

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
            next_allowed = recommendation.last_recommended_at + timedelta(days=RECOMMENDATION_CYCLE_DAYS)
            if timezone.now() < next_allowed:
                # Within 365 days — return existing stored data
                return self._serialize_recommendation(recommendation)

        # First time or 365 days passed — call AI (structured scores only, no raw Q&A)
        structured_input = AssessmentContextBuilder.build_llm_input(assessment)

        payload = RecommendationPipeline.run(structured_assessment=structured_input)

        recommendation = self._save_recommendation(assessment, user, payload, recommendation)
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
            existing.save(update_fields=["raw_ai_response", "easy_decision_making", "last_recommended_at", "updated_at", "updated_by"])
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
        existing_suggestions = list(recommendation.suggestions.all().order_by("display_order"))
        for order, suggestion in enumerate(payload.top_suggestions, start=1):
            edu = suggestion.required_education.model_dump() if suggestion.required_education else {}
            factors = suggestion.career_factors.model_dump() if suggestion.career_factors else {}
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
                s.save(update_fields=[
                    "career_name", "match_percentage", "ai_insight",
                    "why_this_career", "required_skills", "required_education",
                    "career_factors", "career_roadmap", "display_order",
                    "updated_at", "updated_by",
                ])
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
        suggestions = [
            {
                "career_name": s.career_name,
                "match_percentage": s.match_percentage,
                "ai_insight": s.ai_insight,
                "why_this_career": s.why_this_career,
                "required_skills": s.required_skills,
                "required_education": s.required_education,
                "career_factors": AIRecommendationService._public_career_factors(
                    s.career_factors
                ),
                "career_roadmap": s.career_roadmap,
                "display_order": s.display_order,
            }
            for s in recommendation.suggestions.all().order_by("display_order")
        ]
        return {
            "top_suggestions": suggestions,
            "easy_decision_making": recommendation.easy_decision_making,
            "last_recommended_at": recommendation.last_recommended_at.isoformat() if recommendation.last_recommended_at else None,
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
