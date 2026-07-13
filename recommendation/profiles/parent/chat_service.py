from __future__ import annotations

from assessment_career.models import (
    ChatMessage,
    ChatSession,
    CareerRecommendation,
    CareerSuggestion,
)
from recommendation.engine.chat_service import (
    BaseAIChatService,
    CAREER_SCOPE_REFUSAL_PREFIX,
)
from recommendation.engine.chat_helpers import (
    as_list,
    format_education,
    format_other_suggestions,
)


def _build_parent_career_context(suggestion) -> str:
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


def _get_parent_chips(suggestion) -> list[str]:
    career = (suggestion.career_name or "this career").strip()
    skills = as_list(suggestion.required_skills)
    first_skill = skills[0] if skills else ""
    questions = []
    if first_skill:
        questions.append(f"How important is {first_skill} for {career}?")
    else:
        questions.append(f"What skills should my child build first for {career}?")
    questions.append(f"What salary range can my child expect in India for {career}?")
    questions.append(f"What should my child's 6-month roadmap look like for {career}?")
    return questions[:3]


ParentChatService = BaseAIChatService(
    suggestion_model=CareerSuggestion,
    chat_session_model=ChatSession,
    chat_message_model=ChatMessage,
    build_career_context=_build_parent_career_context,
    get_chips=_get_parent_chips,
    profile_type=CareerRecommendation.ProfileType.PARENT,
)
