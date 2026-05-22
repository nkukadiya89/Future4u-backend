from __future__ import annotations

from typing import Any

from recommendation.config import EASY_DECISION_COUNT, TOP_SUGGESTION_COUNT
from recommendation.pipeline.roadmap_normalizer import (
    CAREER_ROADMAP_PHASE_KEYS,
    normalize_career_roadmap,
)
from recommendation.schemas.recommendation_output import (
    EDUCATION_SUGGESTION_MIN,
    clip_ai_insight,
    clip_why_career_reason,
    normalize_education_suggestions,
    normalize_risk_level,
)

_TOP_SUGGESTION_KEYS: tuple[str, ...] = (
    "top_suggestions",
    "topSuggestions",
    "top_suggestion",
    "suggestions",
    "careers",
    "career_suggestions",
    "recommendations",
    "career_recommendations",
)

_NESTED_PAYLOAD_KEYS: tuple[str, ...] = ("data", "result", "response", "output", "payload")


def coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        for sep in ("\n", ";", "|"):
            if sep in text:
                return [p.strip() for p in text.split(sep) if p.strip()]
        if "," in text:
            return [p.strip() for p in text.split(",") if p.strip()]
        return [text]
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, dict):
                text = (
                    str(item.get("text") or item.get("reason") or item.get("label") or "")
                ).strip()
            else:
                text = str(item).strip()
            if text:
                out.append(text)
        return out
    return [str(value).strip()] if str(value).strip() else []


def coerce_int(value: Any, *, low: int = 0, high: int = 100) -> int | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, bool):
            number = int(value)
        elif isinstance(value, (int, float)):
            number = int(round(float(value)))
        else:
            text = str(value).strip().rstrip("%")
            number = int(round(float(text)))
    except (TypeError, ValueError):
        return None
    return max(low, min(high, number))


def normalize_job_security(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        return {"level": text, "description": None, "market_demand_growth": None}
    if not isinstance(value, dict):
        return None
    data = dict(value)
    level = str(data.get("level") or data.get("security") or "").strip() or None
    description = str(
        data.get("description")
        or data.get("market_demand_growth")
        or data.get("demand")
        or ""
    ).strip()
    market = str(data.get("market_demand_growth") or description or "").strip()
    return {
        "level": level,
        "description": description or None,
        "market_demand_growth": market or None,
    }


def normalize_learning_curve(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        return {"level": text, "description": None}
    if not isinstance(value, dict):
        return None
    data = dict(value)
    level = str(data.get("level") or data.get("curve") or "").strip() or None
    description = str(data.get("description") or data.get("detail") or "").strip()
    return {"level": level, "description": description or None}


def normalize_salary(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        return {"average": text, "growth_rate": None}
    if isinstance(value, (int, float)):
        return {"average": str(value), "growth_rate": None}
    if not isinstance(value, dict):
        return None
    data = dict(value)
    average = data.get("average") or data.get("range") or data.get("salary")
    growth = data.get("growth_rate") or data.get("growth")
    return {
        "average": str(average).strip() if average is not None else None,
        "growth_rate": str(growth).strip() if growth is not None else None,
    }


def normalize_career_factors(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        if isinstance(value, str) and value.strip():
            return {"growth_potential": value.strip()}
        return None
    data = dict(value)
    if "salary" in data:
        data["salary"] = normalize_salary(data.get("salary"))
    if "job_security" in data:
        data["job_security"] = normalize_job_security(data.get("job_security"))
    if "learning_curve" in data:
        data["learning_curve"] = normalize_learning_curve(data.get("learning_curve"))
    if "risk_level" in data:
        data["risk_level"] = normalize_risk_level(data.get("risk_level"))
    if "skill_match" in data:
        data["skill_match"] = coerce_int(data.get("skill_match"))
    return data


def normalize_required_education(value: Any) -> dict[str, Any] | None:
    """Coerce shape only; never invent degree suggestions."""
    if value is None:
        return None
    if isinstance(value, str):
        suggestions = normalize_education_suggestions([value])
    elif isinstance(value, list):
        suggestions = normalize_education_suggestions(coerce_string_list(value))
    elif isinstance(value, dict):
        data = dict(value)
        raw = data.get("suggestions")
        if raw is None and data.get("primary_degree"):
            raw = [data["primary_degree"]]
        suggestions = normalize_education_suggestions(coerce_string_list(raw))
    else:
        return None

    if not suggestions:
        return None
    if len(suggestions) < EDUCATION_SUGGESTION_MIN and len(suggestions) >= 1:
        while len(suggestions) < EDUCATION_SUGGESTION_MIN:
            suggestions.append(suggestions[-1])
    return {"suggestions": suggestions}


def extract_top_suggestions_raw(payload: dict[str, Any]) -> list[Any]:
    for key in _NESTED_PAYLOAD_KEYS:
        nested = payload.get(key)
        if isinstance(nested, dict):
            found = extract_top_suggestions_raw(nested)
            if found:
                return found

    top_raw: Any = None
    for key in _TOP_SUGGESTION_KEYS:
        if key in payload:
            top_raw = payload[key]
            break

    if top_raw is None:
        return []

    if isinstance(top_raw, dict):
        if not top_raw:
            return []
        if any(
            key in top_raw
            for key in ("career_name", "career", "name", "title", "match_percentage")
        ):
            return [top_raw]
        if all(isinstance(value, dict) for value in top_raw.values()):
            items: list[dict[str, Any]] = []
            for key, value in top_raw.items():
                item = dict(value)
                if not str(item.get("career_name") or item.get("name") or "").strip():
                    item["career_name"] = str(key).strip()
                items.append(item)
            return items
        return []

    if isinstance(top_raw, str):
        return [top_raw]

    if isinstance(top_raw, list):
        return top_raw

    return []


def normalize_top_suggestion(item: Any) -> dict[str, Any] | None:
    """Coerce LLM fields; drop items missing required AI-generated content."""
    if isinstance(item, str):
        name = item.strip()
        if not name:
            return None
        return None
    if not isinstance(item, dict):
        return None

    data = dict(item)
    career_name = str(
        data.get("career_name")
        or data.get("career")
        or data.get("name")
        or data.get("title")
        or data.get("job_title")
        or ""
    ).strip()
    if not career_name:
        return None

    match = coerce_int(
        data.get("match_percentage") or data.get("match") or data.get("score")
    )
    if match is None:
        return None

    ai_insight = clip_ai_insight(data.get("ai_insight") or data.get("insight") or "")
    if not ai_insight.strip():
        return None

    why = [
        clip_why_career_reason(v)
        for v in coerce_string_list(data.get("why_this_career"))
        if str(v).strip()
    ][:5]
    if not why:
        return None

    skills = coerce_string_list(data.get("required_skills") or data.get("skills"))[:20]
    if not skills:
        return None

    education = normalize_required_education(data.get("required_education"))
    if not education:
        return None

    roadmap_raw = data.get("career_roadmap") or data.get("roadmap")
    if not isinstance(roadmap_raw, dict):
        return None
    career_roadmap = normalize_career_roadmap(roadmap_raw)
    if not all(career_roadmap.get(phase) for phase in CAREER_ROADMAP_PHASE_KEYS):
        return None

    normalized: dict[str, Any] = {
        "career_name": career_name,
        "match_percentage": match,
        "ai_insight": ai_insight,
        "why_this_career": why,
        "required_skills": skills,
        "required_education": education,
        "career_roadmap": career_roadmap,
    }
    if item.get("career_factors") is not None:
        normalized["career_factors"] = normalize_career_factors(item.get("career_factors"))
    return normalized


def normalize_easy_decision_item(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    data = {k: v for k, v in item.items() if k != "reason"}
    title = str(data.get("title") or "").strip()
    career_name = str(
        data.get("career_name") or data.get("career") or data.get("name") or ""
    ).strip()
    if not title or not career_name:
        return None
    return {"title": title, "career_name": career_name}


def normalize_easy_decisions(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep only valid LLM easy-decision rows; no synthetic cards."""
    cleaned = [
        row
        for row in (normalize_easy_decision_item(x) for x in items)
        if row is not None
    ]
    return cleaned[:EASY_DECISION_COUNT]


def normalize_raw_payload(data: Any) -> dict[str, Any]:
    """Coerce malformed LLM JSON; never inject template or database text."""
    if not isinstance(data, dict):
        return {}

    payload = dict(data)
    top_raw = extract_top_suggestions_raw(payload)
    top_suggestions: list[dict[str, Any]] = []
    for item in top_raw:
        normalized = normalize_top_suggestion(item)
        if normalized:
            top_suggestions.append(normalized)

    payload["top_suggestions"] = top_suggestions[:TOP_SUGGESTION_COUNT]

    easy_raw = payload.get("easy_decision_making")
    if not isinstance(easy_raw, list):
        easy_raw = (
            payload.get("easy_decisions")
            or payload.get("easyDecisions")
            or payload.get("easy_decision")
            or []
        )
    payload["easy_decision_making"] = normalize_easy_decisions(
        easy_raw if isinstance(easy_raw, list) else []
    )
    return payload
