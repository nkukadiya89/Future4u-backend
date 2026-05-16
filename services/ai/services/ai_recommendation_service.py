from __future__ import annotations

import logging

from decouple import config
from django.db.models import Prefetch

from assessment.models import Option, StudentAssessment, UserResponse
from services.ai.context.assessment_context_builder import AssessmentContextBuilder
from services.ai.exceptions import (
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from services.ai.clients.openai_client import get_openai_api_key
from services.ai.context.recommendation_response_builder import RecommendationResponseBuilder
from services.ai.generators.ai_recommendation_generator import AIRecommendationGenerator
from services.ai.retrieval.career_knowledge_retriever import CareerKnowledgeRetriever

logger = logging.getLogger(__name__)


class AIRecommendationService:
    """Orchestrates assessment → signals → PostgreSQL → OpenAI → validated JSON."""

    def generate(self, *, assessment_id: int, user) -> dict:
        assessment = self._load_assessment(assessment_id)
        if assessment.user_id != user.id:
            raise AssessmentAccessDeniedError("Assessment access denied")

        self._ensure_ready(assessment)

        student_signals = AssessmentContextBuilder.build(assessment)
        career_candidates = CareerKnowledgeRetriever.retrieve(assessment)

        if not career_candidates:
            domain_code = getattr(assessment.domain, "domain_code", None)
            raise AssessmentNotReadyError(
                "No careers found for the selected domain. "
                f"Ensure domain '{domain_code}' has domain-career mappings "
                "(python manage.py init_domain_career_mappings) or scoring/report metadata."
            )

        use_openai = config("AI_USE_OPENAI", default=True, cast=bool)
        if use_openai:
            get_openai_api_key()
            payload = AIRecommendationGenerator.generate(
                student_signals=student_signals,
                career_candidates=career_candidates,
            )
            return payload.model_dump()

        logger.info(
            "AI_USE_OPENAI=false: using deterministic builder (dev only; not OpenAI output)"
        )
        return RecommendationResponseBuilder.build(
            student_signals=student_signals,
            career_candidates=career_candidates,
        ).model_dump()

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
