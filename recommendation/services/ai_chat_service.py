from __future__ import annotations

from typing import Any

from django.db import transaction

from assessment_career.models import (
    CareerRecommendationChatMessage,
    CareerRecommendationChatSession,
    CareerRecommendationSuggestion,
)
from recommendation.clients.llm_client import get_chat_model
from recommendation.exceptions import (
    AIConfigurationError,
    AIGenerationError,
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
)
from recommendation.prompts.ai_chat_prompt import build_ai_chat_prompt
from recommendation.services.ai_recommendation_service import AI_RECOMMENDATION_DISCLAIMER

MAX_QUESTION_LENGTH = 500
CHAT_MAX_TOKENS = 450
SUMMARY_MAX_CHARS = 600
SUMMARY_MAX_TURNS = 3
MESSAGE_PREVIEW_MAX_CHARS = 120
MESSAGES_RETURN_LIMIT = 30
CAREER_SCOPE_REFUSAL_PREFIX = (
    "I can only answer questions related to this career recommendation."
)


class AIChatService:
    """Career-specific chatbot over a saved AI recommendation."""

    def context(self, *, user, assessment_id: int, suggestion_id: int | str) -> dict[str, Any]:
        suggestion = self._get_suggestion(
            user=user,
            assessment_id=assessment_id,
            suggestion_id=parse_suggestion_id(suggestion_id),
        )
        session = get_existing_chat_session(suggestion)
        return {
            **chat_context_response(suggestion),
            "messages": serialize_messages(session),
        }

    def ask(
        self,
        *,
        user,
        assessment_id: int,
        suggestion_id: int | str,
        question: str,
    ) -> dict[str, Any]:
        question = (question or "").strip()
        if not question:
            raise ValueError("Message is required")
        if len(question) > MAX_QUESTION_LENGTH:
            raise ValueError(f"Message must be {MAX_QUESTION_LENGTH} characters or less")

        suggestion = self._get_suggestion(
            user=user,
            assessment_id=assessment_id,
            suggestion_id=parse_suggestion_id(suggestion_id),
        )
        session = get_chat_session(suggestion)

        reused_answer = find_reused_answer(session=session, question=question)
        if reused_answer:
            return {
                **chat_context_response(suggestion),
                "answer": reused_answer,
                "messages": serialize_messages(session),
            }

        answer = self._ask_llm(
            suggestion=suggestion,
            question=question,
            summary=session.summary,
        )
        save_chat_turn(session=session, question=question, answer=answer)

        return {
            **chat_context_response(suggestion),
            "answer": answer,
            "messages": serialize_messages(session),
        }

    @staticmethod
    def _get_suggestion(*, user, assessment_id: int, suggestion_id: int):
        suggestion = (
            CareerRecommendationSuggestion.objects.filter(
                id=suggestion_id,
                recommendation__assessment_id=assessment_id,
                recommendation__user=user,
                recommendation__deleted=False,
                deleted=False,
            )
            .select_related("recommendation", "recommendation__assessment")
            .first()
        )
        if suggestion:
            return suggestion

        exists_for_assessment = CareerRecommendationSuggestion.objects.filter(
            recommendation__assessment_id=assessment_id,
            recommendation__user=user,
            recommendation__deleted=False,
            deleted=False,
        ).exists()
        if exists_for_assessment:
            raise AssessmentAccessDeniedError("Invalid suggestion for this assessment")
        raise AssessmentNotFoundError("Recommendation not found for this assessment")

    @staticmethod
    def _ask_llm(*, suggestion, question: str, summary: str) -> str:
        try:
            chain = build_ai_chat_prompt() | get_chat_model(max_tokens=CHAT_MAX_TOKENS)
            response = chain.invoke(
                {
                    "career_context": build_career_context(suggestion),
                    "conversation_summary": format_summary(summary),
                    "question": question,
                }
            )
        except AIConfigurationError:
            raise
        except Exception as exc:
            raise AIGenerationError(_format_chat_error(exc)) from exc

        content = getattr(response, "content", response)
        answer = str(content or "").strip()
        if not answer:
            raise AIGenerationError("AI chat returned an empty answer")
        return answer


def chat_context_response(suggestion) -> dict[str, Any]:
    chips = chips_for(suggestion)
    return {
        "career_name": suggestion.career_name,
        "suggestion_id": suggestion.id,
        "match_percentage": suggestion.match_percentage,
        "ai_insight": suggestion.ai_insight,
        "why_this_career": _as_list(suggestion.why_this_career),
        "chips": chips,
        "disclaimer": AI_RECOMMENDATION_DISCLAIMER,
    }


def get_chat_session(suggestion) -> CareerRecommendationChatSession:
    session, _ = CareerRecommendationChatSession.objects.get_or_create(
        suggestion=suggestion
    )
    return session


def get_existing_chat_session(suggestion) -> CareerRecommendationChatSession | None:
    return CareerRecommendationChatSession.objects.filter(suggestion=suggestion).first()


def normalize_chat_question(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def find_reused_answer(
    *,
    session: CareerRecommendationChatSession,
    question: str,
) -> str:
    normalized_question = normalize_chat_question(question)
    if not normalized_question:
        return ""

    messages = list(
        session.messages.filter(deleted=False).order_by("created_at", "id")
    )
    for user_message, assistant_message in reversed(list(zip(messages, messages[1:]))):
        if (
            user_message.role == CareerRecommendationChatMessage.ROLE_USER
            and assistant_message.role == CareerRecommendationChatMessage.ROLE_ASSISTANT
            and normalize_chat_question(user_message.content) == normalized_question
        ):
            return assistant_message.content

    return ""


def save_chat_turn(
    *,
    session: CareerRecommendationChatSession,
    question: str,
    answer: str,
) -> None:
    with transaction.atomic():
        CareerRecommendationChatMessage.objects.create(
            session=session,
            role=CareerRecommendationChatMessage.ROLE_USER,
            content=question,
        )
        CareerRecommendationChatMessage.objects.create(
            session=session,
            role=CareerRecommendationChatMessage.ROLE_ASSISTANT,
            content=answer,
        )
        if should_add_to_summary(answer):
            session.summary = update_summary(
                current=session.summary,
                question=question,
                answer=answer,
            )
            session.save(update_fields=["summary", "updated_at"])


def serialize_messages(
    session: CareerRecommendationChatSession | None,
) -> list[dict[str, Any]]:
    if not session:
        return []
    messages = session.messages.filter(deleted=False).order_by(
        "-created_at", "-id"
    )[:MESSAGES_RETURN_LIMIT]
    return [
        {
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at,
        }
        for message in reversed(list(messages))
    ]


def parse_suggestion_id(value: int | str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("Suggestion id must be a valid number") from None


def build_career_context(suggestion) -> str:
    lines = [
        f"Career: {suggestion.career_name}",
        f"Match: {suggestion.match_percentage}%",
        f"Insight: {suggestion.ai_insight}",
        f"Why this career: {', '.join(_as_list(suggestion.why_this_career)[:4])}",
        f"Skills: {', '.join(_as_list(suggestion.required_skills)[:8])}",
        f"Education: {format_education(suggestion.required_education)}",
        f"Career factors: {format_career_factors(suggestion.career_factors)}",
        f"Roadmap: {format_roadmap(suggestion.career_roadmap)}",
        f"Other suggested careers: {format_other_suggestions(suggestion)}",
    ]
    return "\n".join(line for line in lines if line and not line.endswith(": "))


def format_education(value: Any) -> str:
    if isinstance(value, dict):
        suggestions = _as_list(value.get("suggestions"))
        if suggestions:
            return ", ".join(suggestions[:3])
        label = _education_label(value)
        return label or "Not specified"
    return _education_label(value) or "Not specified"


def format_career_factors(value: Any) -> str:
    if not isinstance(value, dict):
        return compact_text(value, 350) if value else "Not specified"

    salary = value.get("salary") or {}
    salary_text = ""
    if isinstance(salary, dict):
        average = str(salary.get("average") or "").strip()
        growth = str(salary.get("growth_rate") or "").strip()
        salary_text = " ".join(part for part in (average, growth) if part)

    job_security = value.get("job_security") or {}
    job_text = ""
    if isinstance(job_security, dict):
        level = str(job_security.get("level") or "").strip()
        demand = str(job_security.get("market_demand_growth") or "").strip()
        job_text = " ".join(part for part in (level, demand) if part)

    learning_curve = value.get("learning_curve") or {}
    learning_text = ""
    if isinstance(learning_curve, dict):
        learning_text = str(learning_curve.get("level") or "").strip()

    parts = [
        f"salary {salary_text}" if salary_text else "",
        f"growth {value.get('growth_potential')}" if value.get("growth_potential") else "",
        f"work-life {value.get('work_life_balance')}" if value.get("work_life_balance") else "",
        f"job security {job_text}" if job_text else "",
        f"skill match {value.get('skill_match')}%" if value.get("skill_match") is not None else "",
        f"learning curve {learning_text}" if learning_text else "",
        f"risk {value.get('risk_level')}" if value.get("risk_level") else "",
    ]
    return "; ".join(part for part in parts if part) or "Not specified"


def format_roadmap(value: Any) -> str:
    if not isinstance(value, dict):
        return compact_text(value, 350) if value else "Not specified"

    phase_labels = {
        "next_3_months": "0-3 months",
        "next_3_to_6_months": "3-6 months",
        "next_6_to_9_months": "6-9 months",
        "next_9_to_12_months": "9-12 months",
    }
    steps = []
    for key, label in phase_labels.items():
        tasks = value.get(key) or []
        if not isinstance(tasks, list) or not tasks:
            continue
        first_task = tasks[0]
        if isinstance(first_task, dict):
            title = str(first_task.get("task_title") or "").strip()
            description = str(first_task.get("task_description") or "").strip()
            text = title or description
        else:
            text = str(first_task).strip()
        if text:
            steps.append(f"{label}: {compact_text(text, 80)}")
    return "; ".join(steps) or "Not specified"


def format_other_suggestions(suggestion) -> str:
    other_suggestions = (
        suggestion.recommendation.suggestions.filter(deleted=False)
        .exclude(id=suggestion.id)
        .order_by("display_order", "id")[:2]
    )
    rows = [
        f"{item.display_order}. {item.career_name} ({item.match_percentage}% match): {item.ai_insight}"
        for item in other_suggestions
    ]
    return "; ".join(rows) or "None"


def format_summary(summary: str) -> str:
    return (summary or "").strip() or "No previous conversation."


def update_summary(*, current: str, question: str, answer: str) -> str:
    question_preview = compact_text(question, MESSAGE_PREVIEW_MAX_CHARS)
    answer_preview = compact_text(answer, MESSAGE_PREVIEW_MAX_CHARS)
    turn = f"Q: {question_preview} A: {answer_preview}"
    turns = [line.strip() for line in (current or "").splitlines() if line.strip()]
    turns.append(turn)
    summary = "\n".join(turns[-SUMMARY_MAX_TURNS:])
    while len(summary) > SUMMARY_MAX_CHARS and len(turns) > 1:
        turns = turns[1:]
        summary = "\n".join(turns[-SUMMARY_MAX_TURNS:])
    return summary[-SUMMARY_MAX_CHARS:].lstrip()


def should_add_to_summary(answer: str) -> bool:
    return not str(answer or "").strip().startswith(CAREER_SCOPE_REFUSAL_PREFIX)


def compact_text(value: str, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def chips_for(suggestion) -> list[str]:
    career = (suggestion.career_name or "this career").strip()
    skills = _as_list(suggestion.required_skills)
    first_skill = skills[0] if skills else ""
    education = _education_label(suggestion.required_education)
    salary = _factor_value(suggestion.career_factors, "salary")
    growth = _factor_value(suggestion.career_factors, "growth_potential")

    questions = []
    if first_skill:
        questions.append(f"How important is {first_skill} for {career}?")
    else:
        questions.append(f"What skills should I build first for {career}?")

    if salary:
        questions.append(f"What does this salary mean for a beginner in India?")
    else:
        questions.append(f"What salary range can I expect in India for {career}?")

    if education:
        questions.append(f"Is {education} enough to start in {career}?")
    elif growth:
        questions.append(f"How stable is {career} for the next few years?")
    else:
        questions.append(f"What should my 6-month roadmap look like for {career}?")

    return questions[:3]


def _education_label(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("minimum", "recommended", "degree", "qualification", "suggestions"):
            item = value.get(key)
            if isinstance(item, list):
                text = str(item[0] if item else "").strip()
            else:
                text = str(item or "").strip()
            if text:
                return text
    if isinstance(value, str):
        return value.strip()
    return ""


def _factor_value(value: Any, key: str) -> str:
    if isinstance(value, dict):
        item = value.get(key)
        if isinstance(item, dict):
            return str(item.get("value") or item.get("average") or "").strip()
        return str(item or "").strip()
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("label") or "").casefold()
            if key.replace("_", " ") in name:
                return str(item.get("value") or "").strip()
    return ""


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _format_chat_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    if "quota" in lowered or "429" in lowered or "rate limit" in lowered:
        return "AI chat is busy right now. Please try again shortly."
    return "Unable to answer right now. Please try again."
