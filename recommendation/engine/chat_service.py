from __future__ import annotations

from typing import Any, Callable

from django.db import transaction

from recommendation.clients.llm_client import get_chat_model
from recommendation.exceptions import (
    AIConfigurationError,
    AIGenerationError,
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
)
from recommendation.engine.ai_chat_prompt import build_ai_chat_prompt
from utils.token_usage import extract_token_usage
from recommendation.engine.chat_helpers import (
    as_list,
    format_education,
    format_summary,
    update_summary,
    parse_suggestion_id,
    serialize_messages,
    format_other_suggestions,
    format_chat_error,
    MAX_QUESTION_LENGTH,
    CHAT_MAX_TOKENS,
)

CAREER_SCOPE_REFUSAL_PREFIX = (
    "I can only answer questions related to this career recommendation."
)


class BaseAIChatService:

    def __init__(
        self,
        *,
        suggestion_model,
        chat_session_model,
        chat_message_model,
        build_career_context: Callable,
        get_chips: Callable,
        profile_type: str | None = None,
    ):
        self._suggestion_model = suggestion_model
        self._chat_session_model = chat_session_model
        self._chat_message_model = chat_message_model
        self._build_career_context = build_career_context
        self._get_chips = get_chips
        self._profile_type = profile_type

    def __call__(self):
        return self

    def context(self, *, user, assessment_id: int, suggestion_id: int | str) -> dict:
        suggestion = self._get_suggestion(
            user=user,
            assessment_id=assessment_id,
            suggestion_id=parse_suggestion_id(suggestion_id),
        )
        session = self._get_existing_chat_session(suggestion)
        return {
            **self._chat_context(suggestion, session=session),
            "messages": serialize_messages(session),
        }

    def ask(
        self, *, user, assessment_id: int, suggestion_id: int | str, question: str
    ) -> dict:
        question = (question or "").strip()
        if not question:
            raise ValueError("Message is required")
        if len(question) > MAX_QUESTION_LENGTH:
            raise ValueError(
                f"Message must be {MAX_QUESTION_LENGTH} characters or less"
            )

        suggestion = self._get_suggestion(
            user=user,
            assessment_id=assessment_id,
            suggestion_id=parse_suggestion_id(suggestion_id),
        )
        session = self._get_chat_session(suggestion)

        reused = self._find_reused_answer(session=session, question=question)
        if reused:
            return {
                **self._chat_context(suggestion, session=session),
                "answer": reused,
                "messages": serialize_messages(session),
                "_token_usage": 0,
            }

        answer, token_usage = self._ask_llm(
            suggestion=suggestion,
            question=question,
            summary=session.summary,
        )
        self._save_chat_turn(session=session, question=question, answer=answer)

        response = {
            **self._chat_context(suggestion, session=session),
            "answer": answer,
            "messages": serialize_messages(session),
        }
        response["_token_usage"] = token_usage
        return response

    def _get_suggestion(self, *, user, assessment_id: int, suggestion_id: int):
        from django.db.models import Q

        base_queryset = self._suggestion_model.objects.filter(
            recommendation__user=user,
            recommendation__deleted=False,
            deleted=False,
        )
        if self._profile_type:
            base_queryset = base_queryset.filter(
                recommendation__profile_type=self._profile_type
            )

        assessment_queryset = base_queryset.filter(
            Q(recommendation__student_assessment_id=assessment_id)
            | Q(recommendation__parent_assessment_id=assessment_id)
            | Q(recommendation__professional_assessment_id=assessment_id)
        )
        suggestion = (
            assessment_queryset.filter(id=suggestion_id)
            .select_related("recommendation")
            .first()
        )
        if suggestion:
            return suggestion

        if assessment_queryset.exists():
            raise AssessmentAccessDeniedError("Invalid suggestion for this assessment")
        raise AssessmentNotFoundError("Recommendation not found for this assessment")

    def _ask_llm(self, *, suggestion, question: str, summary: str) -> tuple[str, int]:
        token_usage = 0
        try:
            chain = build_ai_chat_prompt() | get_chat_model(max_tokens=CHAT_MAX_TOKENS)
            response = chain.invoke(
                {
                    "career_context": self._build_career_context(suggestion),
                    "conversation_summary": format_summary(summary),
                    "question": question,
                }
            )
            token_usage = extract_token_usage(response)
        except AIConfigurationError:
            raise
        except Exception as exc:
            raise AIGenerationError(format_chat_error(exc)) from exc

        content = getattr(response, "content", response)
        answer = str(content or "").strip()
        if not answer:
            raise AIGenerationError("AI chat returned an empty answer")
        return answer, token_usage

    def _chat_context(self, suggestion, session=None) -> dict:
        from recommendation.engine.recommendation_service import (
            AI_RECOMMENDATION_DISCLAIMER,
        )

        ctx = {
            "career_name": suggestion.career_name,
            "suggestion_id": suggestion.id,
            "match_percentage": suggestion.match_percentage,
            "ai_insight": suggestion.ai_insight,
            "why_this_career": as_list(suggestion.why_this_career),
            "chips": self._get_chips(suggestion),
            "disclaimer": AI_RECOMMENDATION_DISCLAIMER,
        }
        # Include child_id for parent profile chats (no extra query — reads from FK column directly)
        if session is not None and session.child_id is not None:
            ctx["child_id"] = session.child_id
        return ctx

    def _get_chat_session(self, suggestion):
        session, created = self._chat_session_model.objects.get_or_create(
            suggestion=suggestion
        )
        if created:
            self._set_session_child(session, suggestion)
        return session

    def _set_session_child(self, session, suggestion):
        """Denormalize child_id onto ChatSession for parent profile chats."""
        rec = suggestion.recommendation
        if rec.profile_type == "parent" and rec.parent_assessment_id:
            from assessment.models import ParentAssessment

            child_id = (
                ParentAssessment.objects.filter(id=rec.parent_assessment_id)
                .values_list("child_id", flat=True)
                .first()
            )
            if child_id:
                self._chat_session_model.objects.filter(id=session.id).update(
                    child_id=child_id
                )

    def _get_existing_chat_session(self, suggestion):
        return self._chat_session_model.objects.filter(suggestion=suggestion).first()

    def _find_reused_answer(self, *, session, question: str) -> str:
        normalized = " ".join(str(question or "").strip().casefold().split())
        if not normalized:
            return ""

        messages = list(
            session.messages.filter(deleted=False).order_by("created_at", "id")
        )
        for user_msg, assistant_msg in reversed(list(zip(messages, messages[1:]))):
            if (
                user_msg.role == self._chat_message_model.ROLE_USER
                and assistant_msg.role == self._chat_message_model.ROLE_ASSISTANT
                and " ".join(str(user_msg.content or "").strip().casefold().split())
                == normalized
            ):
                return assistant_msg.content
        return ""

    def _save_chat_turn(self, *, session, question: str, answer: str) -> None:
        with transaction.atomic():
            self._chat_message_model.objects.create(
                session=session,
                role=self._chat_message_model.ROLE_USER,
                content=question,
            )
            self._chat_message_model.objects.create(
                session=session,
                role=self._chat_message_model.ROLE_ASSISTANT,
                content=answer,
            )
            if not str(answer or "").strip().startswith(CAREER_SCOPE_REFUSAL_PREFIX):
                session.summary = update_summary(
                    current=session.summary, question=question, answer=answer
                )
            session.save(update_fields=["summary", "updated_at"])
