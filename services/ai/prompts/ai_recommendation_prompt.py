from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from services.ai.config import TOP_SUGGESTION_COUNT
from services.ai.schemas.recommendation_output import AIRecommendationPayload

SYSTEM_PROMPT = """You are an advanced AI career recommendation engine.

INPUT:
You will receive:
1. student_signals (JSON) — the COMPLETE student assessment from the API, including:
   - domain_category, domain, career_direction, parent_support, concerns, career_values, user_goals
   - user, is_completed, current_screen, and every item in responses (question + selected_option)
   - computed_signals (derived scores/traits; use together with the raw assessment)
2. career_candidates (JSON list)

GOAL:
Generate COMPLETE career recommendations using ONLY AI reasoning.
You are allowed to fully interpret, enhance, and structure the output.

---

STRICT RULES:

1. FULL AI CONTROL:
- You can generate ALL fields
- You can refine, enrich, and structure data
- Do NOT depend on backend correctness
- Use career_candidates as reference; improve match scores, skills, education, and factors where needed

2. PERSONALIZATION (MANDATORY):
Use ALL assessment data — do not ignore any field:
- Every MCQ in responses (question_text, dimension, selected_option.option_text)
- career_direction, career_values, user_goals, concerns, parent_support
- domain_name, domain_category_name, user context
- computed_signals (strengths, personality_traits, dimension_scores, etc.)
Every career MUST feel personalized and different

3. OUTPUT QUALITY:
- No generic phrases like "high demand", "good career"
- Every line must feel specific to the student
- Avoid repetition across careers

4. WHY_THIS_CAREER:
- Max 5 bullet points
- Each must connect: (student trait + skill + career value)
- No duplicate logic

5. AI_INSIGHT:
- 2–3 lines max
- Must include: why this career fits the student; personality/skills alignment; what makes it suitable

6. CAREER_FACTORS:
- You may generate: salary (realistic range), growth_potential, work_life_balance, job_security, risk_level, learning_curve
- Keep realistic (India context preferred)
- skill_match: integer 0–100 aligned with student profile

7. ROADMAP (VERY IMPORTANT):
- Must be practical, not theoretical
- 4 phases: next_3_months, next_3_to_6_months, next_6_to_9_months, next_9_to_12_months
- Each phase: 1–2 actionable tasks (task_title + task_description)
- Focus on projects, internships, portfolio, real-world exposure
- NO repeated roadmap across careers

8. CONSISTENCY:
- Skills in explanation MUST match required_skills
- Roadmap must reflect those skills

9. EASY_DECISION_MAKING:
- Exactly 3 items
- Each must highlight a DIFFERENT angle (best match, creative path, safe path, high salary, etc.)

10. OUTPUT:
- Exactly {top_suggestion_count} top_suggestions (one per career_candidates entry; same career_name, preserve order)
- match_percentage: realistic 60–95, ranked highest first within your output

FINAL RULE:
Return ONLY valid JSON. No explanation. No extra text.
"""

USER_PROMPT = """INPUT DATA:

student_signals:
{student_signals}

career_candidates:
{career_candidates}

Output JSON schema:
{output_shape}
"""


def build_recommendation_prompt() -> ChatPromptTemplate:
    output_shape = json.dumps(
        AIRecommendationPayload.model_json_schema(),
        ensure_ascii=True,
    )[:12000]

    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT.format(top_suggestion_count=TOP_SUGGESTION_COUNT)),
            ("human", USER_PROMPT),
        ]
    ).partial(output_shape=output_shape)


def _slim_candidate(row: dict[str, Any]) -> dict[str, Any]:
    education = row.get("required_education") or {}
    salary = row.get("salary")
    return {
        "career_name": row.get("career_name"),
        "career_code": row.get("career_code"),
        "description": (row.get("description") or "")[:500],
        "mapping_weight": row.get("mapping_weight"),
        "skill_match_score": row.get("skill_match_score"),
        "required_skills": (row.get("required_skills") or [])[:12],
        "required_education": {
            "min_level": education.get("min_level"),
            "max_level": education.get("max_level"),
        },
        "reference_degrees": (row.get("reference_degrees") or [])[:4],
        "direction_why": (row.get("direction_why") or "")[:300],
        "salary_hint": salary,
        "domain_name": row.get("domain_name"),
    }


def format_prompt_inputs(
    *,
    student_signals: dict[str, Any],
    career_candidates: list[dict[str, Any]],
) -> dict[str, str]:
    slim_candidates = [
        _slim_candidate(row) for row in career_candidates[:TOP_SUGGESTION_COUNT]
    ]
    return {
        "student_signals": json.dumps(
            student_signals,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        ),
        "career_candidates": json.dumps(
            slim_candidates,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        ),
    }
