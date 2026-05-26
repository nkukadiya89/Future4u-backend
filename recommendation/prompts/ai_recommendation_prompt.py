from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from recommendation.config import (
    EASY_DECISION_CAREER_COUNT,
    EASY_DECISION_COUNT,
    TOP_SUGGESTION_COUNT,
)
from recommendation.schemas.recommendation_output import (
    AI_INSIGHT_MAX_WORDS,
    AI_INSIGHT_MIN_WORDS,
    AIRecommendationPayload,
    EDUCATION_SUGGESTION_MAX,
    EDUCATION_SUGGESTION_MIN,
    ROADMAP_MAX_WORDS,
    ROADMAP_MIN_WORDS,
    WHY_CAREER_MAX_BULLETS,
    WHY_CAREER_MAX_WORDS,
    WHY_CAREER_MIN_WORDS,
)

SYSTEM_PROMPT = """You are an advanced AI career recommendation engine.

INPUT (JSON only - no raw question text or response rows):
- domain, domain_category: chosen career area
- selected_answer_signals: selected option meanings grouped by interest, aptitude, personality, work_style
- dimension_scores: conservative numeric signals (0.0-1.0). For normal MCQ preference answers these may stay neutral.
- career_direction, parent_support, concerns, career_values, user_goals: pass-through from assessment (use as-is)
- is_completed: boolean

LOGIC:
1. Use domain/domain_category as the main career area.
2. Use selected_answer_signals to understand the student's actual preferences and behaviour.
3. Use dimension_scores only as supporting signal, not as exact scoring when selected answers are MCQ preferences.
4. Use career_direction, user_goals, concerns, career_values, and parent_support for personalization.
5. Choose exactly {top_suggestion_count} distinct career paths for this domain.
6. Do NOT invent question text; use only provided selected answer meanings and profile lists.

RULES:
- Generate every output field yourself; no pre-selected career list from backend.
- required_skills, education, roadmap, and insights must be UNIQUE per career.
- why_this_career: max {why_career_max_bullets} bullets, {why_career_min_words}–{why_career_max_words} words each.
- ai_insight: exactly {ai_insight_min_words}–{ai_insight_max_words} words (count before returning), one sentence.
- match_percentage: integers 60–95, descending across the three careers.
- required_education.suggestions: {education_suggestion_min}–{education_suggestion_max} items.
- career_roadmap: 4 phases with task_title + task_description ({roadmap_min_words}–{roadmap_max_words} words each).
- career_factors (required, all from you — backend never fills defaults). Match the Career Factors UI card exactly:
  - salary.average: INR text e.g. "₹6-10 LPA" or "₹18L+"
  - salary.growth_rate: parenthetical badge e.g. "(+125%)" or "(+10%)" (not "5% YoY")
  - growth_potential: Low | Medium | High
  - work_life_balance: Poor | Fair | Good | Excellent
  - job_security.level: Low | Medium | High
  - job_security.market_demand_growth: demand trend only, format "5% | 25%" (two percentages, pipe-separated)
  - skill_match: integer 0–100 (UI shows as percent)
  - learning_curve.level: Low | Medium | High (use Medium not Moderate)
  - learning_curve.description: short subtitle e.g. "To become proficient"
  - risk_level: Low | Medium | High
- easy_decision_making: exactly {easy_decision_count} items comparing top {easy_decision_career_count} careers; titles from: "Best for quick start", "Best for high salary", "Best long term bet", "Most stable career".

Return ONLY valid JSON. No markdown.

Example shape:
{json_shape_example}
"""

_JSON_SHAPE_EXAMPLE = """{
  "top_suggestions": [
    {
      "career_name": "Data Analyst",
      "match_percentage": 88,
      "ai_insight": "Your strong aptitude score and analytical signals align with data storytelling roles.",
      "why_this_career": ["High aptitude fit", "Goals mention data impact"],
      "required_skills": ["Excel", "SQL", "Python basics"],
      "required_education": {"suggestions": ["B.Sc Statistics", "B.Tech IT"]},
      "career_factors": {
        "salary": {"average": "₹6-10 LPA", "growth_rate": "(+12%)"},
        "growth_potential": "High",
        "work_life_balance": "Good",
        "job_security": {
          "level": "High",
          "market_demand_growth": "5% | 25%"
        },
        "skill_match": 84,
        "learning_curve": {
          "level": "Medium",
          "description": "To become proficient"
        },
        "risk_level": "Medium"
      },
      "career_roadmap": {
        "next_3_months": [{"task_title": "Learn SQL fundamentals", "task_description": "Complete beginner SQL course with weekly practice"}],
        "next_3_to_6_months": [{"task_title": "Portfolio project", "task_description": "Publish dashboard using public dataset on GitHub"}],
        "next_6_to_9_months": [{"task_title": "Internship", "task_description": "Apply analytics on real business dataset"}],
        "next_9_to_12_months": [{"task_title": "Interview prep", "task_description": "Practice case studies for analyst roles"}]
      }
    }
  ],
  "easy_decision_making": [
    {"title": "Best for quick start", "career_name": "Data Analyst"},
    {"title": "Best for high salary", "career_name": "Product Manager"}
  ]
}"""


def _escape_langchain_template(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


USER_PROMPT = """structured_assessment:
{structured_assessment}

Output JSON schema:
{output_shape}
"""


def build_recommendation_prompt() -> ChatPromptTemplate:
    output_shape = json.dumps(
        AIRecommendationPayload.model_json_schema(),
        ensure_ascii=True,
    )[:12000]

    system_text = SYSTEM_PROMPT.format(
        top_suggestion_count=TOP_SUGGESTION_COUNT,
        easy_decision_count=EASY_DECISION_COUNT,
        easy_decision_career_count=EASY_DECISION_CAREER_COUNT,
        why_career_min_words=WHY_CAREER_MIN_WORDS,
        why_career_max_words=WHY_CAREER_MAX_WORDS,
        why_career_max_bullets=WHY_CAREER_MAX_BULLETS,
        ai_insight_min_words=AI_INSIGHT_MIN_WORDS,
        ai_insight_max_words=AI_INSIGHT_MAX_WORDS,
        education_suggestion_min=EDUCATION_SUGGESTION_MIN,
        education_suggestion_max=EDUCATION_SUGGESTION_MAX,
        roadmap_min_words=ROADMAP_MIN_WORDS,
        roadmap_max_words=ROADMAP_MAX_WORDS,
        json_shape_example=_JSON_SHAPE_EXAMPLE,
    )
    system_message = _escape_langchain_template(system_text)

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            ("human", USER_PROMPT),
        ]
    ).partial(output_shape=output_shape)


def format_prompt_inputs(*, structured_assessment: dict[str, Any]) -> dict[str, str]:
    return {
        "structured_assessment": json.dumps(
            structured_assessment,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        ),
    }
