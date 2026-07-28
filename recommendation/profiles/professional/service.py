from __future__ import annotations

from assessment.models import ProfessionalAssessment
from assessment_career.models import CareerRecommendation, CareerSuggestion
from recommendation.engine.recommendation_service import (
    load_recommendation_and_check_cycle,
    save_recommendation,
    serialize_recommendation,
)
from recommendation.exceptions import (
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from recommendation.pipeline.recommendation_pipeline import RecommendationPipeline
from recommendation.profiles.professional import prompts as professional_prompts
from recommendation.profiles.professional.context_builder import (
    ProfessionalAssessmentContextBuilder,
)


class ProfessionalRecommendationService:

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

        structured_input = ProfessionalAssessmentContextBuilder.build_llm_input(
            assessment
        )

        payload, token_usage = RecommendationPipeline.run(
            structured_assessment=structured_input,
            build_prompt=professional_prompts.build_recommendation_prompt,
            format_inputs=lambda data, validation_feedback="None": professional_prompts.format_prompt_inputs(
                professional_assessment=data, validation_feedback=validation_feedback
            ),
        )

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
    def _load_assessment(assessment_id: int) -> ProfessionalAssessment:
        try:
            return (
                ProfessionalAssessment.objects.filter(deleted=False)
                .select_related(
                    "user",
                    "domain_category",
                    "domain",
                )
                .prefetch_related(
                    "guidance_reasons",
                    "work_constraints",
                    "career_values",
                    "platform_goals",
                )
                .get(id=assessment_id)
            )
        except ProfessionalAssessment.DoesNotExist as exc:
            raise AssessmentNotFoundError("Assessment not found") from exc

    @staticmethod
    def _ensure_ready(assessment: ProfessionalAssessment) -> None:
        if not assessment.is_completed:
            raise AssessmentNotReadyError(
                "Complete the assessment before generating recommendations."
            )
        if not assessment.domain_id:
            raise AssessmentNotReadyError(
                "Select a domain before generating recommendations."
            )
