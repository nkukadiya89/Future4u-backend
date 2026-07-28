from __future__ import annotations

from typing import Any

from assessment_career.models import (
    CareerRecommendation,
    CareerSuggestion,
    ChatMessage,
    ChatSession,
)
from recommendation.engine.chat_helpers import (
    as_list,
    compact_text,
    format_education,
    format_other_suggestions,
)
from recommendation.engine.chat_service import BaseAIChatService


def _build_professional_career_context(suggestion) -> str:
    lines = [
        f"Career: {suggestion.career_name}",
        f"Match: {suggestion.match_percentage}%",
        f"Insight: {suggestion.ai_insight}",
        f"Why this career: {', '.join(as_list(suggestion.why_this_career)[:4])}",
        f"Skills: {', '.join(as_list(suggestion.required_skills)[:8])}",
        f"Education: {format_education(suggestion.required_education)}",
        f"Other suggested careers: {format_other_suggestions(suggestion)}",
    ]
    return "\n".join(line for line in lines if line and not line.endswith(": "))


def _get_professional_chips(suggestion) -> list[str]:
    career = (suggestion.career_name or "this career").strip()
    skills = as_list(suggestion.required_skills)
    first_skill = skills[0] if skills else ""

    questions = []
    if first_skill:
        questions.append(f"How important is {first_skill} for {career}?")
    else:
        questions.append(f"What skills do I need to transition into {career}?")

    questions.append(f"What salary range can I expect in India for {career}?")
    questions.append(f"What does a 6-month roadmap look like for {career}?")

    return questions[:3]


ProfessionalChatService = BaseAIChatService(
    suggestion_model=CareerSuggestion,
    chat_session_model=ChatSession,
    chat_message_model=ChatMessage,
    build_career_context=_build_professional_career_context,
    get_chips=_get_professional_chips,
    profile_type=CareerRecommendation.ProfileType.PROFESSIONAL,
)
