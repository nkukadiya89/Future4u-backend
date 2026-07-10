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
    {"title": "Best for high salary", "career_index": 1},
    {"title": "Best long term bet", "career_index": 2},
    {"title": "Most stable career", "career_index": 0}
  ]
}"""


def _escape_langchain_template(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


def build_prompt(system_text: str, user_prompt_template: str) -> ChatPromptTemplate:
    system_text = system_text.format(
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
            ("human", user_prompt_template),
        ]
    )


def format_inputs(
    data_key: str,
    assessment_data: dict[str, Any],
    mode_instructions: str,
) -> dict[str, str]:
    return {
        data_key: json.dumps(
            assessment_data,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        ),
        "mode_instructions": mode_instructions,
    }
