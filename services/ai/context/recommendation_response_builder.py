from __future__ import annotations

from typing import Any

from services.ai.exceptions import RecommendationDataIncompleteError
from services.ai.schemas.recommendation_output import (
    AIRecommendationPayload,
    EasyDecisionItem,
    TopSuggestionItem,
)


def _task(title: str, description: str) -> dict[str, str]:
    return {"task_title": title.strip(), "task_description": description.strip()}


def _roadmap_from_row(row: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    steps = [
        str(s).strip()
        for s in (row.get("career_roadmap") or {}).get("steps", [])
        if str(s).strip()
    ]
    career_name = row.get("career_name") or row.get("career_code") or "career"
    if len(steps) < 6:
        raise RecommendationDataIncompleteError(
            f"Roadmap needs at least 6 steps for '{career_name}' "
            f"(found {len(steps)}). Seed domain_report_meta next_step_1/2/3 and "
            "domain_counsellor_knowledge.action for this domain."
        )

    return {
        "next_3_months": [
            _task("Step 1", steps[0]),
            _task("Step 2", steps[1]),
        ],
        "next_6_to_12_months": [
            _task("Step 3", steps[2]),
            _task("Step 4", steps[3]),
        ],
        "next_12_to_18_months": [
            _task("Step 5", steps[4]),
            _task("Step 6", steps[5]),
        ],
    }


def _primary_degree(row: dict[str, Any]) -> str:
    degrees = list((row.get("career_roadmap") or {}).get("degrees") or [])
    if degrees:
        return " / ".join(degrees[:3])

    edu = row.get("required_education") or {}
    min_level = (edu.get("min_level") or "").strip()
    if min_level:
        return min_level

    min_code = (edu.get("min_level_code") or "").strip()
    if min_code:
        return min_code

    career_name = row.get("career_name") or row.get("career_code") or "career"
    raise RecommendationDataIncompleteError(
        f"Education requirements are missing for '{career_name}'. "
        "Configure career min_education_level or domain_report_meta degrees."
    )


def _required_skills(row: dict[str, Any]) -> list[str]:
    skills = [str(s).strip() for s in (row.get("required_skills") or []) if str(s).strip()]
    if not skills:
        career_name = row.get("career_name") or row.get("career_code") or "career"
        raise RecommendationDataIncompleteError(
            f"Required skills are missing for '{career_name}'. "
            "Seed domain_skill_mapping for this domain."
        )
    return skills[:8]


def _salary_factor(row: dict[str, Any]) -> dict[str, str]:
    future_scope = (row.get("future_scope") or "").strip()
    if not future_scope:
        career_name = row.get("career_name") or "career"
        raise RecommendationDataIncompleteError(
            f"Future scope note is missing for '{career_name}'. "
            "Seed domain_report_meta.note."
        )

    salary = row.get("salary")
    if isinstance(salary, dict):
        salary_min = salary.get("min")
        salary_max = salary.get("max")
        if salary_min is not None and salary_max is not None:
            average = f"₹{int(salary_min):,}–₹{int(salary_max):,}"
            return {"average": average, "growth_rate": future_scope}
        if salary_min is not None:
            return {"average": f"₹{int(salary_min):,}+", "growth_rate": future_scope}
        if salary_max is not None:
            return {"average": f"Up to ₹{int(salary_max):,}", "growth_rate": future_scope}

    insight = (row.get("industry_trends") or "").strip()
    if insight:
        return {"average": insight, "growth_rate": future_scope}

    career_name = row.get("career_name") or "career"
    raise RecommendationDataIncompleteError(
        f"Salary context is missing for '{career_name}'. "
        "Seed domain_counsellor_knowledge.insight or domain_report_meta.note."
    )


def _work_life_balance(row: dict[str, Any], stored: dict[str, Any]) -> str:
    work_modes = row.get("work_environment") or []
    if work_modes:
        return ", ".join(str(m) for m in work_modes[:3])

    tension = (stored.get("tension") or "").strip()
    if tension:
        return tension

    tradeoff = (stored.get("tradeoff") or "").strip()
    if tradeoff:
        return tradeoff

    career_name = row.get("career_name") or "career"
    raise RecommendationDataIncompleteError(
        f"Work-life context is missing for '{career_name}'. "
        "Seed domain_counsellor_knowledge.tension or tradeoff."
    )


def _career_factors_from_row(*, row: dict[str, Any], skill_match: int) -> dict[str, Any]:
    future_scope = (row.get("future_scope") or "").strip()
    if not future_scope:
        career_name = row.get("career_name") or "career"
        raise RecommendationDataIncompleteError(
            f"Future scope is missing for '{career_name}'. "
            "Seed domain_report_meta.note."
        )

    insight = (row.get("industry_trends") or "").strip()
    if not insight:
        career_name = row.get("career_name") or "career"
        raise RecommendationDataIncompleteError(
            f"Counsellor insight is missing for '{career_name}'. "
            "Seed domain_counsellor_knowledge.insight."
        )

    stored = row.get("career_factors") or {}
    tradeoff = (stored.get("tradeoff") or "").strip()
    if not tradeoff:
        career_name = row.get("career_name") or "career"
        raise RecommendationDataIncompleteError(
            f"Career tradeoff is missing for '{career_name}'. "
            "Seed domain_counsellor_knowledge.tradeoff."
        )

    listings = int(row.get("active_listings") or 0)

    factors: dict[str, Any] = {
        "salary": _salary_factor(row),
        "growth_potential": future_scope,
        "work_life_balance": _work_life_balance(row, stored),
        "job_security": {
            "level": str(listings) if listings > 0 else future_scope,
            "market_demand_growth": future_scope,
        },
        "skill_match": skill_match,
        "learning_curve": {"level": insight, "description": insight},
        "risk_level": tradeoff,
    }

    tension = (stored.get("tension") or "").strip()
    if tension:
        factors["tension"] = tension

    return factors


def _ai_insight(row: dict[str, Any]) -> str:
    insight = (row.get("industry_trends") or "").strip()
    if insight:
        return insight

    direction_why = (row.get("direction_why") or "").strip()
    if direction_why:
        return direction_why

    career_name = row.get("career_name") or "career"
    raise RecommendationDataIncompleteError(
        f"AI insight text is missing for '{career_name}'. "
        "Seed domain_counsellor_knowledge.insight or domain_report_meta.direction_why."
    )


def _why_this_career(row: dict[str, Any], skills: list[str]) -> list[str]:
    reasons: list[str] = []

    direction_why = (row.get("direction_why") or "").strip()
    if direction_why:
        reasons.append(direction_why)

    future_scope = (row.get("future_scope") or "").strip()
    if future_scope:
        reasons.append(future_scope)

    stored = row.get("career_factors") or {}
    tradeoff = (stored.get("tradeoff") or "").strip()
    if tradeoff:
        reasons.append(tradeoff)

    tension = (stored.get("tension") or "").strip()
    if tension:
        reasons.append(tension)

    if skills:
        reasons.append(f"Skills from domain_skill_mapping: {', '.join(skills[:5])}.")

    if not reasons:
        career_name = row.get("career_name") or "career"
        raise RecommendationDataIncompleteError(
            f"No 'why this career' content for '{career_name}'. "
            "Seed domain_report_meta and domain_counsellor_knowledge."
        )

    return reasons[:5]


class RecommendationResponseBuilder:
    """Build frontend recommendations from PostgreSQL rows (CSV-seeded masters only)."""

    MAX_SUGGESTIONS = 3

    @classmethod
    def build(
        cls,
        *,
        student_signals: dict[str, Any],
        career_candidates: list[dict[str, Any]],
    ) -> AIRecommendationPayload:
        if not career_candidates:
            raise RecommendationDataIncompleteError("No career candidates to build recommendations.")

        ranked = sorted(
            career_candidates,
            key=lambda row: int(row.get("mapping_weight") or 0),
            reverse=True,
        )[: cls.MAX_SUGGESTIONS]

        top_suggestions: list[TopSuggestionItem] = []
        for row in ranked:
            career_name = str(row.get("career_name") or "").strip()
            if not career_name:
                raise RecommendationDataIncompleteError("Career name missing in database row.")

            weight = int(row.get("mapping_weight") or 0)
            if weight <= 0:
                raise RecommendationDataIncompleteError(
                    f"Invalid mapping weight for career '{career_name}'."
                )

            match_percentage = max(0, min(100, weight))
            skill_match_raw = row.get("skill_match_score")
            if skill_match_raw is None:
                raise RecommendationDataIncompleteError(
                    f"Skill match score is missing for '{career_name}'. "
                    "Seed domain_skill_mapping with weight_score for this domain."
                )
            skill_match = max(0, min(100, int(skill_match_raw)))
            skills = _required_skills(row)

            top_suggestions.append(
                TopSuggestionItem(
                    career_name=career_name,
                    match_percentage=match_percentage,
                    ai_insight=_ai_insight(row),
                    why_this_career=_why_this_career(row, skills),
                    required_skills=skills,
                    required_education={"primary_degree": _primary_degree(row)},
                    career_factors=_career_factors_from_row(row=row, skill_match=skill_match),
                    career_roadmap=_roadmap_from_row(row),
                )
            )

        easy: list[EasyDecisionItem] = []
        for idx, (row, suggestion) in enumerate(zip(ranked, top_suggestions)):
            direction_why = (row.get("direction_why") or "").strip()
            title = direction_why[:120] if direction_why else suggestion.career_name
            reason = (row.get("future_scope") or row.get("industry_trends") or "").strip()
            if not reason:
                raise RecommendationDataIncompleteError(
                    f"Easy-decision reason missing for '{suggestion.career_name}'."
                )
            easy.append(
                EasyDecisionItem(
                    title=title,
                    career_name=suggestion.career_name,
                    reason=reason,
                )
            )

        return AIRecommendationPayload(
            top_suggestions=top_suggestions,
            easy_decision_making=easy,
        )
