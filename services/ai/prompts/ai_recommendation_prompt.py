from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """You are Future4u's career counsellor AI.

Rules:
- Pick careers ONLY from career_candidates (use exact career_name values).
- Use database facts as context but WRITE fresh, career-specific prose for each suggestion.
- Do NOT copy the same paragraph into multiple fields or multiple careers.
- Do NOT paste counsellor insight/tradeoff text into salary.average — salary.average must be a plausible INR range or band (e.g. "₹4–8 LPA entry") inferred from the career and domain.
- growth_potential, work_life_balance, and risk_level must be short labels or one sentence each, unique per career.
- match_percentage and skill_match should reflect mapping_weight and student_signals (integers 0–100).
- required_skills must come from that career's required_skills in the payload (spell them clearly).
- required_education.primary_degree from degrees or education fields in the payload.
- career_roadmap: each phase needs 2 items with meaningful task_title (not "Step 1") and actionable task_description grounded in next_steps from the payload.
- why_this_career: 4–5 bullets tailored to THIS career and the student's signals.
- ai_insight: 2–3 sentences personalized to the student and this career only.
- easy_decision_making: exactly 3 items with distinct titles and reasons (not identical to other careers).

Return JSON matching the schema exactly. Produce exactly 3 top_suggestions when at least 3 candidates exist.
"""

USER_PROMPT = """Student signals:
{student_signals}

Career candidates (database):
{career_candidates}

Reference JSON structure (follow this shape exactly):
{output_shape}
"""


def build_recommendation_prompt() -> ChatPromptTemplate:
    output_shape = json.dumps(
        {
            "top_suggestions": [
                {
                    "career_name": "Example Career",
                    "match_percentage": 82,
                    "ai_insight": "Two to three personalized sentences.",
                    "why_this_career": ["reason 1", "reason 2", "reason 3", "reason 4"],
                    "required_skills": ["Skill A", "Skill B", "Skill C"],
                    "required_education": {"primary_degree": "B.Tech in relevant field"},
                    "career_factors": {
                        "salary": {"average": "₹18L+", "growth_rate": "+125%"},
                        "growth_potential": "Very High",
                        "work_life_balance": "Good",
                        "job_security": {"level": "High", "market_demand_growth": "25%"},
                        "skill_match": 80,
                        "learning_curve": {
                            "level": "Medium",
                            "description": "Requires continuous learning.",
                        },
                        "risk_level": "Medium",
                    },
                    "career_roadmap": {
                        "next_3_months": [
                            {
                                "task_title": "Explore fundamentals",
                                "task_description": "Learn core concepts.",
                            }
                        ],
                        "next_6_to_12_months": [],
                        "next_12_to_18_months": [],
                    },
                }
            ],
            "easy_decision_making": [
                {
                    "title": "Best Match Overall",
                    "career_name": "Example Career",
                    "reason": "Short reason.",
                }
            ],
        },
        ensure_ascii=True,
    )

    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ]
    ).partial(output_shape=output_shape)


def format_prompt_inputs(
    *,
    student_signals: dict[str, Any],
    career_candidates: list[dict[str, Any]],
) -> dict[str, str]:
    return {
        "student_signals": json.dumps(student_signals, ensure_ascii=True, separators=(",", ":")),
        "career_candidates": json.dumps(
            career_candidates, ensure_ascii=True, separators=(",", ":")
        ),
    }
