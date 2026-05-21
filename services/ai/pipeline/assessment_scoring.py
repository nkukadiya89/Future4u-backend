from __future__ import annotations

import statistics
from typing import Any

DIMENSION_KEYS = ("interest", "aptitude", "personality", "work_style")

# option_text keyword → signal (checked case-insensitively)
_OPTION_TEXT_SIGNALS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("independent", "alone", "self-directed", "own pace"), "prefers independent work"),
    (("team", "collaborat", "group", "people"), "values teamwork and collaboration"),
    (("structure", "routine", "plan", "organized"), "values structured tasks"),
    (("flexible", "adapt", "variety", "change"), "adapts well to changing priorities"),
    (("deep", "theory", "concept", "understand"), "learns concepts deeply"),
    (("hands-on", "practical", "build", "apply"), "prefers hands-on application"),
    (("feedback", "improve", "grow", "learn from"), "accepts feedback for growth"),
    (("lead", "initiative", "decide"), "comfortable taking initiative"),
    (("creative", "design", "imagine", "ideas"), "drawn to creative problem-solving"),
    (("data", "logic", "analy", "numbers"), "leans toward analytical thinking"),
    (("help", "support", "empath", "care"), "motivated by helping others"),
    (("detail", "accuracy", "precise"), "pays attention to detail"),
)

# High agreement (sequence 3–4) per dimension when option text has no keyword hit
_DIMENSION_HIGH_SIGNALS: dict[str, str] = {
    "interest": "shows strong curiosity about the field",
    "aptitude": "confident in learning technical or analytical skills",
    "personality": "communicates and collaborates effectively",
    "work_style": "prefers clear goals and steady execution",
}

_DIMENSION_LOW_SIGNALS: dict[str, str] = {
    "interest": "explores interests cautiously before committing",
    "aptitude": "builds skills gradually with guided practice",
    "personality": "works best with time to reflect before acting",
    "work_style": "prefers flexibility over rigid structure",
}


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


def _response_option_text(response: dict[str, Any]) -> str:
    option = response.get("selected_option") or {}
    return str(option.get("option_text") or "").strip()


def calculate_dimension_scores(responses: list[dict[str, Any]]) -> dict[str, float]:
    """
    Group by question dimension; normalize mean(sequence_order) / 4 → 0–1.
    sequence_order is expected on a 1–4 scale (values above 4 are clamped).
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


def _signal_from_option_text(option_text: str) -> str | None:
    lowered = option_text.lower()
    if not lowered:
        return None
    for keywords, signal in _OPTION_TEXT_SIGNALS:
        if any(word in lowered for word in keywords):
            return signal
    return None


def _signal_from_dimension_agreement(dimension: str, order: int) -> str | None:
    if order >= 3:
        return _DIMENSION_HIGH_SIGNALS.get(dimension)
    if order <= 2:
        return _DIMENSION_LOW_SIGNALS.get(dimension)
    return None


def extract_behavior_signals(responses: list[dict[str, Any]]) -> list[str]:
    """
    Derive 3–5 short human-readable traits from dimension + selected option text.
    """
    seen: set[str] = set()
    signals: list[str] = []

    def add(signal: str | None) -> None:
        if not signal:
            return
        text = signal.strip()
        if not text or text in seen:
            return
        seen.add(text)
        signals.append(text)

    for response in responses or []:
        dim = _response_dimension(response)
        if not dim:
            continue
        order = _response_sequence_order(response)
        option_text = _response_option_text(response)

        add(_signal_from_option_text(option_text))
        add(_signal_from_dimension_agreement(dim, order))
        if len(signals) >= 5:
            break

    if len(signals) < 3:
        scores = calculate_dimension_scores(responses)
        for dim in sorted(DIMENSION_KEYS, key=lambda k: scores.get(k, 0.5), reverse=True):
            add(_DIMENSION_HIGH_SIGNALS.get(dim))
            if len(signals) >= 3:
                break

    return signals[:5]


def _compact_string_list(value: Any, *, limit: int = 8) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()][:limit]
    text = str(value).strip()
    return [text] if text else []


def build_ai_input(data: dict[str, Any]) -> dict[str, Any]:
    """
    LLM payload: responses → dimension_scores only; all other assessment fields as-is.
    Never includes raw question_text, option_text, or the responses array.
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

    payload: dict[str, Any] = {
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
    return payload
