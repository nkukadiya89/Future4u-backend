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
- ai_insight is one warm mentor-tone sentence grounded in the student's actual profile data - not generic observations.
- Use respectful student-facing language; avoid labels like "low-skill", "weak", "poor fit", or wording that sounds discouraging. Avoid absolute or guaranteed-sounding wording; prefer careful confidence language such as "strong fit", "aligns well", "good match", or "promising path" when describing career fit.
- why_this_career: max {why_career_max_bullets} bullets, {why_career_min_words}-{why_career_max_words} words each.
- ai_insight: {ai_insight_min_words}-{ai_insight_max_words} words, one sentence.
- match_percentage: integers 60-95, descending across the three careers.
- required_education.levels: an array of objects with EXACT keys: type, level_key, name.
- required_education.levels.level_key MUST be one of:
  secondary, higher_secondary, diploma, graduation, post_graduation, doctorate, professional, certification
- If you do not know levels, return required_education.levels as [] (empty array). Never use null.
- career_roadmap must include EXACT phase keys: next_3_months, next_3_to_6_months, next_6_to_9_months, next_9_to_12_months.
- Each career_roadmap phase contains task_title + task_description ({roadmap_min_words}-{roadmap_max_words} words each).
- Every career_roadmap item must use ONLY these keys: task_title and task_description.
- The JSON example below shows response shape only.
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
- Compare only the top {easy_decision_career_count} careers. Use career_index to reference top_suggestions: 0 for first, 1 for second, 2 for third. Reuse a career_index only when evidence clearly supports it.

MODE:
__MODE_INSTRUCTIONS__

Return ONLY valid JSON using this shape:
{output_shape}
"""

OUTPUT_SHAPE = """{
  "top_suggestions": [
    {
      "career_name": "Career Name",
      "match_percentage": 88,
      "ai_insight": "8-18 word personalized sentence",
      "why_this_career": ["5-12 word concrete reason"],
      "required_skills": ["Skill name"],
      "required_education": {
        "levels": [
          {"type": "Display label", "level_key": "graduation", "name": "Course or degree name"}
        ]
      },
      "career_factors": {
        "salary": {"average": "INR X-Y LPA", "growth_rate": "(+10%)"},
        "growth_potential": "High",
        "work_life_balance": "Good",
        "job_security": {"level": "High", "market_demand_growth": "5% | 25%"},
        "skill_match": 80,
        "learning_curve": {"level": "Medium", "description": "To become proficient"},
        "risk_level": "Medium"
      },
      "career_roadmap": {
        "next_3_months": [{"task_title": "Short action title", "task_description": "8-24 word action sentence"}],
        "next_3_to_6_months": [{"task_title": "Short action title", "task_description": "8-24 word action sentence"}],
        "next_6_to_9_months": [{"task_title": "Short action title", "task_description": "8-24 word action sentence"}],
        "next_9_to_12_months": [{"task_title": "Short action title", "task_description": "8-24 word action sentence"}]
      }
    }
  ],
  "easy_decision_making": [
    {"title": "Best for quick start", "career_index": 0},
    {"title": "Best for high salary", "career_index": 0},
    {"title": "Best long term bet", "career_index": 0},
    {"title": "Most stable career", "career_index": 0}
  ]
}"""


NORMAL_MODE_INSTRUCTIONS = (
    'Normal career mode: use career/job-readiness roadmap tasks and India INR salary.'
)


STUDY_ABROAD_MODE_INSTRUCTIONS = """Study Abroad mode:
- Keep ranking career/domain based; only adapt insight, reasons, education, roadmap, and salary.
- salary.average should use an India INR range and describe abroad earnings as variable by country, visa status, degree level, and local demand.
- Education should use realistic global course-style paths, not country-specific degree abbreviations unless provided in structured_assessment. Avoid fake universities, vague "international programs", and guaranteed routes.
- Roadmap uses readiness stages with exact titles: "Start now: country & budget", "Next: course & exams", "Before applying: documents & profile", "Final check: apply safely".
- Keep roadmap descriptions short and practical: budget, course fit, eligibility, intake, documents, portfolio, visa/refund checks, and backup planning where relevant.
- Keep exam guidance conditional and requirement-based when country or course details are unknown.
- In the course/exams stage, include category-level checks for English proficiency, postgraduate/advanced aptitude where relevant, and German/French or other language requirements.
- Avoid naming country-specific exams unless provided in structured_assessment.
- Avoid generic abroad phrases and guaranteed admission, visa, job, PR, scholarship, or salary claims."""


def _escape_langchain_template(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


USER_PROMPT = "structured_assessment:\n{structured_assessment}"


def _is_study_abroad_mode(structured_assessment: dict[str, Any]) -> bool:
    career_direction = structured_assessment.get("career_direction") or []
    if isinstance(career_direction, str):
        values = [career_direction]
    elif isinstance(career_direction, list):
        values = career_direction
    else:
        values = []
    return any(str(value).strip().casefold() == "study abroad" for value in values)


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
        roadmap_min_words=ROADMAP_MIN_WORDS,
        roadmap_max_words=ROADMAP_MAX_WORDS,
        output_shape=OUTPUT_SHAPE,
    )
    system_message = _escape_langchain_template(system_text).replace(
        "__MODE_INSTRUCTIONS__",
        "{mode_instructions}",
    )

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
        "mode_instructions": (
            STUDY_ABROAD_MODE_INSTRUCTIONS
            if _is_study_abroad_mode(structured_assessment)
            else NORMAL_MODE_INSTRUCTIONS
        ),
    }
