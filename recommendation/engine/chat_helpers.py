from __future__ import annotations

from typing import Any

from utils.datetime_formatter import format_datetime

# Shared constants used by profile-specific chat services.
MAX_QUESTION_LENGTH = 500
CHAT_MAX_TOKENS = 450
SUMMARY_MAX_CHARS = 600
SUMMARY_MAX_TURNS = 3
MESSAGE_PREVIEW_MAX_CHARS = 120
MESSAGES_RETURN_LIMIT = 30


def as_list(value: Any) -> list[str]:
    """Normalise a value to a list of trimmed strings."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def compact_text(value: str, max_chars: int) -> str:
    """Truncate text cleanly with an ellipsis."""
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def format_summary(summary: str) -> str:
    return (summary or "").strip() or "No previous conversation."


def update_summary(*, current: str, question: str, answer: str) -> str:
    """Append the latest Q&A turn to the rolling summary."""
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


def parse_suggestion_id(value: int | str) -> int:
    """Coerce a raw suggestion-id value to an int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("Suggestion id must be a valid number")


def serialize_messages(session) -> list[dict[str, Any]]:
    """Return the most recent N messages in chronological order."""
    if not session:
        return []
    messages = session.messages.filter(deleted=False).order_by("-created_at", "-id")[
        :MESSAGES_RETURN_LIMIT
    ]
    return [
        {
            "role": message.role,
            "content": message.content,
            "created_at": format_datetime(message.created_at),
        }
        for message in reversed(list(messages))
    ]


def format_other_suggestions(suggestion) -> str:
    """Format up to 2 other career suggestions for the LLM context."""
    others = (
        suggestion.recommendation.suggestions.filter(deleted=False)
        .exclude(id=suggestion.id)
        .order_by("display_order")[:2]
    )
    rows = [
        f"{item.display_order}. {item.career_name} ({item.match_percentage}% match): {item.ai_insight}"
        for item in others
    ]
    return "; ".join(rows) or "None"


def format_chat_error(exc: Exception) -> str:
    """User-facing error message for chat failures."""
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    if "quota" in lowered or "429" in lowered or "rate limit" in lowered:
        return "AI chat is busy right now. Please try again shortly."
    return "Unable to answer right now. Please try again."


def education_label(value: Any) -> str:
    """Extract the first readable education label from a dict/string."""
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


def format_education(value: Any) -> str:
    """Format required_education into a readable string for LLM context."""
    if isinstance(value, dict):
        suggestions = as_list(value.get("suggestions"))
        if suggestions:
            return ", ".join(suggestions[:3])
        label = education_label(value)
        return label or "Not specified"
    return education_label(value) or "Not specified"
