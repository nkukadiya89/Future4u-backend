from __future__ import annotations

import logging

from django.db.models import Prefetch

from assessment.models import Option, StudentAssessment, UserResponse
from services.ai.context.assessment_context_builder import AssessmentContextBuilder
from services.ai.config import TOP_SUGGESTION_COUNT
from services.ai.exceptions import (
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from services.ai.pipeline.recommendation_pipeline import RecommendationPipeline
from services.ai.prompts.ai_recommendation_prompt import career_slots_for_ai
from services.ai.retrieval.career_knowledge_retriever import CareerKnowledgeRetriever

logger = logging.getLogger(__name__)


class AIRecommendationService:
    """Assessment + career title slots → Groq generates full recommendation JSON."""

    def generate(self, *, assessment_id: int, user) -> dict:
        assessment = self._load_assessment(assessment_id)
        if assessment.user_id != user.id:
            raise AssessmentAccessDeniedError("Assessment access denied")

        self._ensure_ready(assessment)

        student_signals = AssessmentContextBuilder.build(assessment)
        computed = student_signals.get("computed_signals") or {}
        student_signals["goals"] = computed.get("user_goals") or student_signals.get(
            "user_goals"
        ) or []

        career_candidates = CareerKnowledgeRetriever.retrieve(assessment)
        if not career_candidates:
            domain_code = getattr(assessment.domain, "domain_code", None)
            raise AssessmentNotReadyError(
                "No careers found for the selected domain. "
                f"Ensure domain '{domain_code}' has domain-career mappings."
            )
        if len(career_slots_for_ai(career_candidates)) < TOP_SUGGESTION_COUNT:
            raise AssessmentNotReadyError(
                "Not enough unique careers for this domain. "
                f"Map at least {TOP_SUGGESTION_COUNT} distinct careers."
            )

        payload = RecommendationPipeline.run(
            student_signals=student_signals,
            career_candidates=career_candidates,
        )
        return payload.model_dump()

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
        has_profile_data = bool(
            assessment.career_direction
            or assessment.career_values
            or assessment.user_goals
        )
        if not has_responses and not has_profile_data and not assessment.is_completed:
            raise AssessmentNotReadyError(
                "Insufficient assessment data. Answer questions or complete the assessment first."
            )
