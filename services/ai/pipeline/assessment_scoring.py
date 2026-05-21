from __future__ import annotations

import statistics
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
    Group by question.dimension; mean(sequence_order) / 4 → 0.0–1.0 (scale 1–4).
    """
    buckets: dict[str, list[int]] = {key: [] for key in DIMENSION_KEYS}

    for response in responses or []:
        dim = _response_dimension(response)
        if not dim:
            continue
        buckets[dim].append(_response_sequence_order(response))

    scores: dict[str, float] = {}
    for dim in DIMENSION_KEYS:
        values = buckets[dim]
        if values:
            scores[dim] = round(statistics.mean(values) / 4.0, 2)
        else:
            scores[dim] = 0.5
    return scores


def _compact_string_list(value: Any, *, limit: int = 8) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()][:limit]
    text = str(value).strip()
    return [text] if text else []


def build_ai_input(data: dict[str, Any]) -> dict[str, Any]:
    """
    LLM payload: responses → dimension_scores; profile fields unchanged.
    No raw questions, option text, or responses array.
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
        "career_direction": _compact_string_list(data.get("career_direction")),
        "parent_support": (str(data.get("parent_support") or "").strip() or None),
        "concerns": _compact_string_list(data.get("concerns")),
        "career_values": _compact_string_list(data.get("career_values")),
        "user_goals": _compact_string_list(data.get("user_goals")),
        "is_completed": bool(data.get("is_completed")),
    }
