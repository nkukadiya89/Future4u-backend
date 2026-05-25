from __future__ import annotations

from typing import Any

DIMENSION_KEYS = ("interest", "aptitude", "personality", "work_style")


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


def calculate_dimension_scores(responses: list[dict[str, Any]]) -> dict[str, float]:
    """
    Keep numeric scores conservative.

    Most questions are MCQ preference questions, where option order is not a
    reliable low-to-high scale. Only scale/yes-no questions use option order as
    a light numeric signal; MCQ meaning is passed separately as text.
    """
    buckets: dict[str, list[int]] = {key: [] for key in DIMENSION_KEYS}

    for response in responses or []:
        dim = _response_dimension(response)
        if not dim:
            continue
        question = response.get("question") or {}
        question_type = (question.get("question_type") or "").strip().lower()
        if question_type not in ("scale", "yesno"):
            continue
        buckets[dim].append(_response_sequence_order(response))

    scores: dict[str, float] = {}
    for dim in DIMENSION_KEYS:
        values = buckets[dim]
        scores[dim] = round((sum(values) / len(values)) / 4.0, 2) if values else 0.5
    return scores


def selected_answer_signals(responses: list[dict[str, Any]]) -> dict[str, list[str]]:
    signals: dict[str, list[str]] = {key: [] for key in DIMENSION_KEYS}
    for response in responses or []:
        dim = _response_dimension(response)
        if not dim:
            continue
        option = response.get("selected_option") or {}
        text = str(option.get("option_text") or "").strip()
        if text and text not in signals[dim]:
            signals[dim].append(text)
    return {key: values[:6] for key, values in signals.items()}


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


def build_ai_input(data: dict[str, Any]) -> dict[str, Any]:
    """
    LLM payload: selected option meanings + conservative dimension scores.
    We avoid raw question text, but keep selected option text because MCQ option
    order is not always a real score.
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
        or ""
    )

    return {
        "domain": str(domain).strip() if domain else None,
        "domain_category": str(domain_category).strip() if domain_category else None,
        "dimension_scores": calculate_dimension_scores(responses),
        "selected_answer_signals": selected_answer_signals(responses),
        "career_direction": _compact_string_list(data.get("career_direction")),
        "parent_support": (str(data.get("parent_support") or "").strip() or None),
        "concerns": _profile_labels(data, "concerns"),
        "career_values": _profile_labels(data, "career_values"),
        "user_goals": _profile_labels(data, "user_goals"),
        "is_completed": bool(data.get("is_completed")),
    }
