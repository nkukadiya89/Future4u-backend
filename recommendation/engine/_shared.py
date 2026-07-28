from __future__ import annotations

from typing import Any

from recommendation.config import EASY_DECISION_COUNT, TOP_SUGGESTION_COUNT
from recommendation.exceptions import AIGenerationError
from recommendation.schemas.recommendation_output import AIRecommendationPayload

# ── Study Abroad mode detection ─────────────────────────────────────


def is_study_abroad_mode(structured_assessment: dict[str, Any]) -> bool:
    """Check if the assessment indicates a study-abroad career direction."""
    career_direction = structured_assessment.get("career_direction") or []
    if isinstance(career_direction, str):
        values = [career_direction]
    elif isinstance(career_direction, list):
        values = career_direction
    else:
        values = []
    return any(str(value).strip().casefold() == "study abroad" for value in values)


# ── LLM error formatting ────────────────────────────────────────────


def format_llm_error(exc: Exception) -> str:
    """User-facing error message for LLM failures."""
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    if "insufficient_quota" in lowered or "quota" in lowered or "429" in lowered:
        return "AI recommendations are busy right now. Please try again shortly."
    return "Unable to generate recommendations right now. Please try again."


def is_retryable_generation_error(exc: AIGenerationError) -> bool:
    """Check if the error is recoverable by retrying the LLM call."""
    message = str(exc).lower()
    return (
        "validation" in message
        or "schema" in message
        or "required recommendation" in message
    )


def is_invalid_model_output(exc: Exception) -> bool:
    """Check if the exception indicates the model returned invalid JSON/output."""
    message = str(exc).lower()
    return (
        "failed to generate json" in message
        or "failed to parse" in message
        or "json_validate_failed" in message
        or "output_parsing_failure" in message
        or "outputparserexception" in message
        or "failed_generation" in message
    )


# ── Payload validation ──────────────────────────────────────────────


def payload_gaps(payload: AIRecommendationPayload) -> list[str]:
    """Check for gaps in the parsed recommendation payload."""
    issues: list[str] = []
    if len(payload.top_suggestions) != TOP_SUGGESTION_COUNT:
        issues.append(
            f"expected {TOP_SUGGESTION_COUNT} top_suggestions, "
            f"got {len(payload.top_suggestions)}"
        )
    names = [s.career_name.strip().casefold() for s in payload.top_suggestions]
    if len(set(names)) != len(names):
        issues.append("duplicate career_name in top_suggestions")
    if len(payload.easy_decision_making) != EASY_DECISION_COUNT:
        issues.append(
            f"expected {EASY_DECISION_COUNT} easy_decision_making, "
            f"got {len(payload.easy_decision_making)}"
        )
    for suggestion in payload.top_suggestions:
        name = suggestion.career_name
        factors = suggestion.career_factors
        if not factors.salary.average.strip():
            issues.append(f"missing salary.average for {name}")
        if not factors.salary.growth_rate.strip():
            issues.append(f"missing salary.growth_rate for {name}")
        if not factors.job_security.market_demand_growth.strip():
            issues.append(f"missing job_security.market_demand_growth for {name}")
        if "|" not in factors.job_security.market_demand_growth:
            issues.append(
                f"job_security.market_demand_growth must use 'X% | Y%' for {name}"
            )
        if not factors.learning_curve.description.strip():
            issues.append(f"missing learning_curve.description for {name}")
    return issues
