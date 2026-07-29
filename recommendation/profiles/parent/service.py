from __future__ import annotations

import logging

from assessment.models import ParentAssessment
from assessment_career.models import CareerRecommendation, CareerSuggestion
from recommendation.engine._shared import is_study_abroad_mode
from recommendation.engine.recommendation_service import (
    load_recommendation_and_check_cycle,
    normalize_study_abroad_payload,
    save_recommendation,
    serialize_recommendation,
)
from recommendation.exceptions import (
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from recommendation.pipeline.recommendation_pipeline import RecommendationPipeline
from recommendation.profiles.parent import prompts as parent_prompts
from recommendation.profiles.parent.context_builder import (
    ParentAssessmentContextBuilder,
)

logger = logging.getLogger(__name__)


class ParentRecommendationService:
    """Parent-specific AI recommendation service."""

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

        structured_input = ParentAssessmentContextBuilder.build_llm_input(assessment)

        payload, token_usage = RecommendationPipeline.run(
            structured_assessment=structured_input,
            build_prompt=parent_prompts.build_parent_recommendation_prompt,
            format_inputs=lambda data, validation_feedback="None": parent_prompts.format_parent_prompt_inputs(
                parent_assessment=data, validation_feedback=validation_feedback
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
    def _load_assessment(assessment_id: int) -> ParentAssessment:
        try:
            return (
                ParentAssessment.objects.filter(deleted=False)
                .select_related(
                    "user",
                    "domain_category",
                    "domain",
                    "child__education_level",
                    "child__stream",
                )
                .prefetch_related(
                    "career_direction",
                    "career_values",
                    "concerns",
                    "parent_career_expectations",
                    "limitations",
                    "user_goals",
                )
                .get(id=assessment_id)
            )
        except ParentAssessment.DoesNotExist:
            raise AssessmentNotFoundError("Assessment not found")

    @staticmethod
    def _ensure_ready(assessment: ParentAssessment) -> None:
        if not assessment.is_completed:
            raise AssessmentNotReadyError(
                "Complete the assessment before generating recommendations."
            )
        if not assessment.child_id or getattr(assessment.child, "deleted", True):
            raise AssessmentNotReadyError(
                "Select a valid child before generating recommendations."
            )
        if not assessment.domain_category_id:
            raise AssessmentNotReadyError(
                "Select a domain category before generating recommendations."
            )
        if not assessment.domain_id:
            raise AssessmentNotReadyError(
                "Select a domain before generating recommendations."
            )
