from __future__ import annotations

from django.db.models import Prefetch

from assessment.models import Option, StudentAssessment, UserResponse
from assessment_career.models import CareerRecommendation, CareerSuggestion
from recommendation.engine.recommendation_service import (
    load_recommendation_and_check_cycle,
    normalize_study_abroad_payload,
    save_recommendation,
    serialize_recommendation,
)
from recommendation.engine._shared import is_study_abroad_mode
from recommendation.exceptions import (
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from recommendation.pipeline.recommendation_pipeline import RecommendationPipeline
from recommendation.profiles.student import prompts as student_prompts
from recommendation.profiles.student.context_builder import AssessmentContextBuilder

__all__ = [
    "StudentRecommendationService",
    "_normalize_study_abroad_payload",
]


class StudentRecommendationService:
    """Student-specific AI recommendation service."""

    def generate(self, *, assessment_id: int, user) -> tuple[dict, int]:
        assessment = self._load_assessment(assessment_id)
        if assessment.user_id != user.id:
            raise AssessmentAccessDeniedError("Assessment access denied")

        self._ensure_ready(assessment)

        recommendation, within_cycle = load_recommendation_and_check_cycle(
            assessment=assessment,
            recommendation_model=CareerRecommendation,
        )
        if within_cycle:
            return serialize_recommendation(recommendation), 0

        structured_input = AssessmentContextBuilder.build_llm_input(assessment)

        payload, token_usage = RecommendationPipeline.run(
            structured_assessment=structured_input,
            build_prompt=student_prompts.build_recommendation_prompt,
            format_inputs=lambda data: student_prompts.format_prompt_inputs(
                student_assessment=data
            ),
        )
        if is_study_abroad_mode(structured_input):
            payload = normalize_study_abroad_payload(payload)

        recommendation = save_recommendation(
            assessment=assessment,
            user=user,
            payload=payload,
            recommendation_model=CareerRecommendation,
            suggestion_model=CareerSuggestion,
            existing=recommendation,
        )
        return serialize_recommendation(recommendation), token_usage

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
