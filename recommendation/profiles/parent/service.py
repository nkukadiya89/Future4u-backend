from __future__ import annotations

import logging

from assessment.models import ParentAssessment
from assessment_career.models import (
    ParentCareerRecommendation,
    ParentCareerRecommendationSuggestion,
)
from pydantic import ValidationError

from recommendation.clients.llm_client import get_chat_model
from recommendation.engine.recommendation_service import (
    AI_RECOMMENDATION_DISCLAIMER,
    load_recommendation_and_check_cycle,
    normalize_study_abroad_payload,
    save_recommendation,
    serialize_recommendation,
)
from recommendation.engine._shared import (
    format_llm_error,
    is_invalid_model_output,
    is_retryable_generation_error,
    is_study_abroad_mode,
    payload_gaps,
)
from recommendation.exceptions import (
    AIConfigurationError,
    AIGenerationError,
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from recommendation.pipeline.payload_validator import parse_ai_payload
from recommendation.pipeline.validated_payload_normalizer import normalize_payload
from recommendation.profiles.parent.context_builder import ParentAssessmentContextBuilder
from recommendation.profiles.parent.prompts import (
    build_parent_recommendation_prompt,
    format_parent_prompt_inputs,
)
from recommendation.schemas.recommendation_output import AIRecommendationPayload

logger = logging.getLogger(__name__)


class ParentAIRecommendationService:
    """Parent-specific AI recommendation service."""

    def generate(self, *, assessment_id: int, user) -> dict:
        assessment = self._load_assessment(assessment_id)
        if assessment.user_id != user.id:
            raise AssessmentAccessDeniedError("Assessment access denied")

        self._ensure_ready(assessment)

        recommendation, within_cycle = load_recommendation_and_check_cycle(
            assessment=assessment,
            recommendation_model=ParentCareerRecommendation,
        )
        if within_cycle:
            return serialize_recommendation(recommendation)

        structured_input = ParentAssessmentContextBuilder.build_llm_input(assessment)

        prompt = build_parent_recommendation_prompt()
        inputs = format_parent_prompt_inputs(
            structured_assessment=structured_input,
        )
        llm = get_chat_model()

        last_error: AIGenerationError | None = None
        for attempt in range(2):
            try:
                payload = self._invoke_once(prompt=prompt, inputs=inputs, llm=llm)
                break
            except AIGenerationError as exc:
                last_error = exc
                if not is_retryable_generation_error(exc) or attempt == 1:
                    raise
                logger.warning(
                    "Retrying parent AI recommendation after invalid response (attempt %d/2)",
                    attempt + 1,
                )
        else:
            raise last_error or AIGenerationError("AI recommendation failed")

        if is_study_abroad_mode(structured_input):
            payload = normalize_study_abroad_payload(payload)

        recommendation = save_recommendation(
            assessment=assessment,
            user=user,
            payload=payload,
            recommendation_model=ParentCareerRecommendation,
            suggestion_model=ParentCareerRecommendationSuggestion,
            existing=recommendation,
        )
        return serialize_recommendation(recommendation)

    @staticmethod
    def _invoke_once(*, prompt, inputs: dict, llm) -> AIRecommendationPayload:
        """Exactly one provider invocation with full validation."""
        try:
            structured_llm = llm.with_structured_output(dict, method="json_mode")
            result = (prompt | structured_llm).invoke(inputs)
        except Exception as exc:
            logger.exception("LLM recommendation generation failed")
            if is_invalid_model_output(exc):
                raise AIGenerationError("AI response failed validation") from exc
            raise AIGenerationError(format_llm_error(exc)) from exc

        try:
            raw = parse_ai_payload(result)
            payload = normalize_payload(raw)
        except ValidationError as exc:
            logger.warning("LLM output validation failed: %s", exc)
            raise AIGenerationError("AI response failed validation") from exc

        gaps = payload_gaps(payload)
        if gaps:
            logger.warning("AI payload shape gaps: %s", "; ".join(gaps))
            raise AIGenerationError(
                "AI response did not meet the required recommendation schema. "
                f"Details: {'; '.join(gaps)}"
            )

        return payload

    @staticmethod
    def _load_assessment(assessment_id: int) -> ParentAssessment:
        try:
            return (
                ParentAssessment.objects.filter(deleted=False)
                .select_related(
                    "user", "domain_category",
                    "child__education_level", "child__stream",
                )
                .prefetch_related(
                    "career_direction", "career_values", "concerns",
                    "parent_career_expectations", "limitations", "user_goals",
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
        if not assessment.domain_category_id:
            raise AssessmentNotReadyError(
                "Select a domain category before generating recommendations."
            )
