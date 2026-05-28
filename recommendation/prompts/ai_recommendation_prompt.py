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
    EDUCATION_SUGGESTION_MAX,
    EDUCATION_SUGGESTION_MIN,
    ROADMAP_MAX_WORDS,
    ROADMAP_MIN_WORDS,
    WHY_CAREER_MAX_BULLETS,
    WHY_CAREER_MAX_WORDS,
    WHY_CAREER_MIN_WORDS,
)

SYSTEM_PROMPT = """You are Future4U's career recommendation engine.

Read the structured assessment and recommend practical career paths.
The child domain/domain_code is the main anchor; domain_category is only broader context.
Use selected_answer_signals as the main assessment meaning.
Use dimension_scores only as light support because many MCQs are preferences, not grades.
Use education_level, stream, goals, concerns, values, parent_support, and career_direction to personalize the result.

RULES:
- Return exactly {top_suggestion_count} distinct careers.
- First career should be the closest practical fit based on both the selected child domain and the student's signals.
- If the student seems unsure or low-confidence, prefer beginner/support roles instead of advanced specialist roles.
- Use a balanced set: closest fit first, then adjacent or contrasting options only when supported by the student's signals.
- Avoid three careers with the same work pattern unless the assessment strongly points to that narrow cluster.
- Adapt education and roadmap to the student's current education level and stream.
- Keep careers, skills, education, roadmap, and insights unique per career.
- Reasons must be concrete: mention actual skills, work style, concern, goal, or field reality.
- ai_insight must name 1-2 specific signals from the input, such as selected answer meaning, education level, stream, concern, value, goal, parent support, or a clearly high/low dimension score.
- Use respectful student-facing language; avoid labels like "low-skill", "weak", "poor fit", or wording that sounds discouraging.
- why_this_career: max {why_career_max_bullets} bullets, {why_career_min_words}-{why_career_max_words} words each.
- ai_insight: {ai_insight_min_words}-{ai_insight_max_words} words, one sentence.
- match_percentage: integers 60-95, descending across the three careers.
- required_education.levels: an array of objects with EXACT keys: type, level_key, name.
- required_education.levels.level_key MUST be one of:
  secondary, higher_secondary, diploma, graduation, post_graduation, doctorate, professional, certification
- If you do not know levels, return required_education.levels as [] (empty array). Never use null.
- career_roadmap: 4 phases with task_title + task_description ({roadmap_min_words}-{roadmap_max_words} words each).
- career_factors must include:
  - salary.average: INR annual range, e.g. "INR 6-10 LPA"
  - salary.growth_rate: parenthetical badge, e.g. "(+10%)"
  - growth_potential: Low | Medium | High
  - work_life_balance: Poor | Fair | Good | Excellent
  - job_security.level: Low | Medium | High
  - job_security.market_demand_growth: "5% | 25%" style demand trend
  - skill_match: integer 0-100
  - learning_curve.level: Low | Medium | High
  - learning_curve.description: short subtitle, e.g. "To become proficient"
  - risk_level: Low | Medium | High
- easy_decision_making must have exactly {easy_decision_count} items with these titles:
  "Best for quick start", "Best for high salary", "Best long term bet", "Most stable career".
- Compare only the top {easy_decision_career_count} careers. Reuse a career only when evidence clearly supports it.

Return ONLY valid JSON using this shape:
{output_shape}
"""

OUTPUT_SHAPE = """{
  "top_suggestions": [
    {
      "career_name": "Data Analyst",
      "match_percentage": 88,
      "ai_insight": "Your strong aptitude score and analytical signals align with data storytelling roles.",
      "why_this_career": ["High aptitude fit", "Goals mention data impact"],
      "required_skills": ["Excel", "SQL", "Python basics"],
      "required_education": {
        "levels": [
          {"type": "Undergraduate", "level_key": "graduation", "name": "B.Sc Statistics"},
          {"type": "Undergraduate", "level_key": "graduation", "name": "B.Tech IT"}
        ]
      },
      "career_factors": {
        "salary": {"average": "INR 6-10 LPA", "growth_rate": "(+12%)"},
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
    {"title": "Best for high salary", "career_name": "Data Analyst"},
    {"title": "Best long term bet", "career_name": "Data Analyst"},
    {"title": "Most stable career", "career_name": "Data Analyst"}
  ]
}"""


def _escape_langchain_template(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


USER_PROMPT = "structured_assessment:\n{structured_assessment}"


def build_recommendation_prompt() -> ChatPromptTemplate:
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
        output_shape=OUTPUT_SHAPE,
    )
    system_message = _escape_langchain_template(system_text)

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            ("human", USER_PROMPT),
        ]
    )


def format_prompt_inputs(*, structured_assessment: dict[str, Any]) -> dict[str, str]:
    return {
        "structured_assessment": json.dumps(
            structured_assessment,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        ),
    }
