from __future__ import annotations

from typing import Any

DIMENSION_KEYS = ("interest", "aptitude", "personality", "work_style")
SIGNAL_WORD_LIMIT = 20
SIGNALS_PER_DIMENSION = 6


def _clamp_sequence_order(raw: Any) -> int:
    try:
        order = int(raw or 1)
    except (TypeError, ValueError):
        return 1
    return max(1, min(4, order))


def _response_dimension(response: dict[str, Any]) -> str:
    question = response.get("question") or {}
    dim = (question.get("dimension") or "").strip().lower()
    return dim if dim in DIMENSION_KEYS else ""


def _response_sequence_order(response: dict[str, Any]) -> int:
    option = response.get("selected_option") or {}
    return _clamp_sequence_order(option.get("sequence_order"))


def _compact_words(value: Any, *, limit: int) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return ""
    words = text.split()
    return " ".join(words[:limit])


def _answer_signal(response: dict[str, Any]) -> str:
    question = response.get("question") or {}
    option = response.get("selected_option") or {}
    question_text = _compact_words(
        question.get("question_text"),
        limit=SIGNAL_WORD_LIMIT,
    )
    option_text = _compact_words(
        option.get("option_text"),
        limit=SIGNAL_WORD_LIMIT,
    )
    seq = _response_sequence_order(response)
    if question_text and option_text:
        return f"{question_text} -> {option_text} [{seq}/4]"
    return option_text


def selected_answer_signals(responses: list[dict[str, Any]]) -> dict[str, list[str]]:
    signals: dict[str, list[str]] = {key: [] for key in DIMENSION_KEYS}
    for response in responses or []:
        dim = _response_dimension(response)
        if not dim:
            continue
        text = _answer_signal(response)
        if text and text not in signals[dim]:
            signals[dim].append(text)
    return {key: values[:SIGNALS_PER_DIMENSION] for key, values in signals.items()}


def _compact_string_list(value: Any, *, limit: int = 8) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()][:limit]
    text = str(value).strip()
    return [text] if text else []


def _profile_labels(data: dict[str, Any], key: str) -> list[str]:
    """Prefer human-readable *_name lists; fall back to legacy key."""
    return _compact_string_list(data.get(f"{key}_name") or data.get(key))


def free_text_responses(responses: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Extract free-text answers from responses (text question_type)."""
    result: list[dict[str, str]] = []
    for r in responses or []:
        question = r.get("question") or {}
        qtype = (question.get("question_type") or "").strip().lower()
        text_answer = r.get("text_answer") or ""
        if qtype == "text" and text_answer.strip():
            result.append({
                "question": _compact_words(question.get("question_text"), limit=15),
                "answer": _compact_words(text_answer, limit=40),
            })
    return result[:5]


def build_ai_input(data: dict[str, Any]) -> dict[str, Any]:
    """
    LLM payload: compact answer signals and profile context.
    We avoid full raw Q&A, but include a short question context with the
    selected option because that carries the assessment meaning for MCQs.
    Free-text answers are included as student_voice for richer context.
    """
    responses = data.get("responses") or []
    if not isinstance(responses, list):
        responses = []

    domain = (
        data.get("domain")
        or data.get("domain_name")
        or data.get("domain_code")
        or ""
    )
    domain_category = (
        data.get("domain_category")
        or data.get("domain_category_name")
        or data.get("domain_category_code")
        or ""
    )

    return {
        "education_level": (
            str(data.get("education_level") or "").strip() or None
        ),
        "stream": str(data.get("stream") or "").strip() or None,
        "domain": str(domain).strip() if domain else None,
        "domain_code": str(data.get("domain_code") or "").strip() or None,
        "domain_category": str(domain_category).strip() if domain_category else None,
        "domain_category_code": (
            str(data.get("domain_category_code") or "").strip() or None
        ),
        "selected_answer_signals": selected_answer_signals(responses),
        "free_text_responses": free_text_responses(responses),
        "career_direction": _compact_string_list(data.get("career_direction")),
        "parent_support": (str(data.get("parent_support") or "").strip() or None),
        "concerns": _profile_labels(data, "concerns"),
        "career_values": _profile_labels(data, "career_values"),
        "user_goals": _profile_labels(data, "user_goals"),
        "is_completed": bool(data.get("is_completed")),
    }
