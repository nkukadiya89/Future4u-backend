from __future__ import annotations

from typing import Any

from recommendation.config import EASY_DECISION_COUNT, TOP_SUGGESTION_COUNT
from recommendation.pipeline.roadmap_normalizer import (
    CAREER_ROADMAP_PHASE_KEYS,
    normalize_career_roadmap,
)
from recommendation.schemas.recommendation_output import (
    clip_ai_insight,
    clip_why_career_reason,
    normalize_education_suggestions,
    normalize_growth_potential,
    normalize_learning_curve_level,
    normalize_risk_level,
    normalize_work_life_balance,
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

_NESTED_PAYLOAD_KEYS: tuple[str, ...] = (
    "data",
    "result",
    "response",
    "output",
    "payload",
)


def coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if "\n" in text:
            # Bulleted/numbered lists: "1. reason\n2. reason" or "- reason\n- reason"
            lines = text.split("\n")
            parts = []
            for line in lines:
                line = line.strip().lstrip("0123456789.)- ")
                if line:
                    parts.append(line)
            if parts:
                return parts
        for sep in (";", "|"):
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
                    str(
                        item.get("text")
                        or item.get("reason")
                        or item.get("label")
                        or ""
                    )
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
        level = normalize_risk_level(text)
        return {"level": level, "market_demand_growth": None}
    if not isinstance(value, dict):
        return None
    data = dict(value)
    level = normalize_risk_level(data.get("level") or data.get("security"))
    market = (
        str(
            data.get("market_demand_growth")
            or data.get("demand_trend")
            or data.get("demand")
            or ""
        ).strip()
        or None
    )
    return {"level": level, "market_demand_growth": market}


def normalize_learning_curve(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        level = normalize_learning_curve_level(text)
        return {"level": level, "description": None}
    if not isinstance(value, dict):
        return None
    data = dict(value)
    level = normalize_learning_curve_level(data.get("level") or data.get("curve"))
    description = (
        str(data.get("description") or data.get("detail") or "").strip() or None
    )
    return {"level": level, "description": description}


_GROWTH_POTENTIAL_KEYS: tuple[str, ...] = (
    "growth_potential",
    "growthPotential",
    "growth",
    "career_growth",
)
_WORK_LIFE_BALANCE_KEYS: tuple[str, ...] = (
    "work_life_balance",
    "workLifeBalance",
    "work_life",
    "work_balance",
    "wlb",
)


def _pick_first_key(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


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
    growth_raw = data.get("growth_potential") or _pick_first_key(
        data, _GROWTH_POTENTIAL_KEYS
    )
    if growth_raw is not None:
        growth_level = normalize_growth_potential(growth_raw)
        if growth_level is not None:
            data["growth_potential"] = growth_level
    balance_raw = data.get("work_life_balance") or _pick_first_key(
        data, _WORK_LIFE_BALANCE_KEYS
    )
    if balance_raw is not None:
        balance_level = normalize_work_life_balance(balance_raw)
        if balance_level is not None:
            data["work_life_balance"] = balance_level
    return data


def normalize_required_education(value: Any) -> dict[str, Any] | None:
    """Coerce required_education into a levels-only shape.

    Input may contain legacy "suggestions" (strings). We convert those into levels
    heuristically so the API always returns:
      {"levels": [{"type": "...", "level_key": "...", "name": "..."}]}
    """
    if value is None:
        return None
    data: dict[str, Any] = {}
    legacy_suggestions: list[str] = []
    if isinstance(value, str):
        legacy_suggestions = normalize_education_suggestions([value])
    elif isinstance(value, list):
        legacy_suggestions = normalize_education_suggestions(coerce_string_list(value))
    elif isinstance(value, dict):
        data = dict(value)
        raw = data.get("suggestions")
        if raw is None and data.get("primary_degree"):
            raw = [data["primary_degree"]]
        legacy_suggestions = normalize_education_suggestions(coerce_string_list(raw))
    else:
        return None

    def _normalize_level_key(raw: Any) -> str:
        text = str(raw or "").strip().lower()
        text = text.replace("-", "_").replace(" ", "_")
        aliases = {
            "10th": "secondary",
            "tenth": "secondary",
            "secondary": "secondary",
            "12th": "higher_secondary",
            "twelfth": "higher_secondary",
            "higher_secondary": "higher_secondary",
            "high_school": "higher_secondary",
            "intermediate": "higher_secondary",
            "diploma": "diploma",
            "graduation": "graduation",
            "undergraduate": "graduation",
            "bachelor": "graduation",
            "bachelors": "graduation",
            "post_graduation": "post_graduation",
            "postgraduation": "post_graduation",
            "postgraduate": "post_graduation",
            "masters": "post_graduation",
            "master": "post_graduation",
            "doctorate": "doctorate",
            "phd": "doctorate",
            "professional": "professional",
            # API expects "professional" for certifications (legacy AI may send certification/certificate).
            "certification": "professional",
            "certificate": "professional",
        }
        return aliases.get(text, "")

    def _normalize_type_label(raw: Any) -> str:
        text = " ".join(str(raw or "").strip().split())
        if not text:
            return ""
        key = text.casefold()
        aliases = {
            "undergraduate": "Undergraduate",
            "ug": "Undergraduate",
            "graduation": "Undergraduate",
            "graduate": "Undergraduate",
            "postgraduate": "Postgraduate",
            "post_graduation": "Postgraduate",
            "pg": "Postgraduate",
            "masters": "Postgraduate",
            "certification": "Certification",
            "certificate": "Certification",
            "professional": "Certification",
        }
        return aliases.get(key, text)

    def _infer_level_from_name(name: str) -> tuple[str, str]:
        n = name.casefold()
        if any(
            k in n for k in ("mba", "m.tech", "mtech", "mca", "m.sc", "msc", "master")
        ):
            return ("Postgraduate", "post_graduation")
        if any(k in n for k in ("b.tech", "btech", "bca", "b.sc", "bsc", "bachelor")):
            return ("Undergraduate", "graduation")
        return ("Certification", "professional")

    def _clean_levels(raw_levels: Any) -> list[dict[str, str]]:
        if raw_levels is None:
            return []
        if isinstance(raw_levels, dict):
            raw_levels = [raw_levels]
        if not isinstance(raw_levels, (list, tuple)):
            return []
        cleaned: list[dict[str, str]] = []
        for item in raw_levels:
            if not isinstance(item, dict):
                continue
            type_label = _normalize_type_label(item.get("type") or item.get("label"))
            level_key = _normalize_level_key(
                item.get("level_key")
                or item.get("levelKey")
                or item.get("key")
                or item.get("level")
            )
            name = str(
                item.get("name") or item.get("degree") or item.get("course") or ""
            ).strip()
            if not type_label or not level_key or not name:
                continue
            cleaned.append({"type": type_label, "level_key": level_key, "name": name})
        return cleaned

    levels: list[dict[str, str]] = []
    if isinstance(value, dict):
        levels = _clean_levels(data.get("levels"))

    # Convert legacy suggestions into levels if levels are missing/empty.
    if not levels and legacy_suggestions:
        converted: list[dict[str, str]] = []
        for s in legacy_suggestions:
            type_label, level_key = _infer_level_from_name(s)
            converted.append({"type": type_label, "level_key": level_key, "name": s})
        levels = converted

    # Always return levels-only; never expose suggestions in API shape.
    return {"levels": levels}


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

    factors_raw = data.get("career_factors") or data.get("careerFactors")
    if factors_raw is None:
        return None
    career_factors = normalize_career_factors(factors_raw)
    if not career_factors:
        return None

    return {
        "career_name": career_name,
        "match_percentage": match,
        "ai_insight": ai_insight,
        "why_this_career": why,
        "required_skills": skills,
        "required_education": education,
        "career_roadmap": career_roadmap,
        "career_factors": career_factors,
    }


def normalize_easy_decision_item(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    data = {k: v for k, v in item.items() if k != "reason"}
    title = str(data.get("title") or "").strip()
    try:
        career_index = int(data.get("career_index"))
    except (TypeError, ValueError):
        return None
    if not title:
        return None
    return {"title": title, "career_index": career_index}


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
