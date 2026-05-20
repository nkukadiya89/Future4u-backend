from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from services.ai.config import (
    EASY_DECISION_CAREER_COUNT,
    EASY_DECISION_COUNT,
    TOP_SUGGESTION_COUNT,
)
from services.ai.schemas.recommendation_output import (
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

INPUT:
You will receive student_signals (JSON) — the COMPLETE student assessment, including:
   - domain_category, domain, career_direction, parent_support, concerns, career_values, user_goals
   - user, is_completed, current_screen, and every item in responses (question + selected_option)
   - computed_signals (derived scores/traits; use together with the raw assessment)

GOAL:
Generate the ENTIRE response using ONLY your reasoning from student_signals.
You must CHOOSE exactly {top_suggestion_count} distinct career paths yourself (career_name values you invent).
Every field in the output JSON must be freshly written by you for this student.
Do NOT assume any pre-selected career list from the backend.

---

STRICT RULES:

1. FULL AI CONTROL:
- YOU choose all {top_suggestion_count} career_name values based on student_signals (domain, traits, goals, responses)
- Generate every field from student_signals only — no external career catalog
- required_skills, required_education.suggestions, ai_insight, career_factors, and career_roadmap must be UNIQUE per career
- NEVER reuse the same required_skills list across multiple careers
- NEVER reuse the same roadmap tasks across multiple careers

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

4. WHY_THIS_CAREER (limits match backend validation in recommendation_output.py):
- Max {why_career_max_bullets} bullet points
- Each bullet: ONLY {why_career_min_words}–{why_career_max_words} words (short phrase, never a full sentence)
- Example: "Strong analytical thinking fits PM" (6 words)
- Each must connect: (student trait + skill + career value)
- No duplicate logic

5. AI_INSIGHT (limits match backend validation in recommendation_output.py):
- MUST be {ai_insight_min_words}–{ai_insight_max_words} words (count carefully). NEVER fewer than {ai_insight_min_words} words.
- One short sentence only; never multiple lines or a paragraph.
- Must say why this career fits the student (traits, skills, goals).
- Too short (reject): "Your analytical mindset fits data analysis" (7 words).
- Good ({ai_insight_max_words} words max): "Your analytical mindset and goal-driven focus align well with product strategy and leadership growth."

6. CAREER_FACTORS:
- You may generate: salary (realistic range), growth_potential, work_life_balance, job_security, risk_level, learning_curve
- risk_level: MUST be exactly one of: "Low", "Medium", "High" (no other labels)
- Keep realistic (India context preferred)
- skill_match: integer 0–100 aligned with student profile
- job_security MUST be an object, never a plain string:
  {{"level": "High", "description": "Strong demand in tech hubs"}}
- learning_curve MUST be an object, never a plain string:
  {{"level": "Moderate", "description": "Needs consistent project practice"}}
- salary MUST be an object, never a plain string:
  {{"average": "6-10 LPA", "growth_rate": "12% YoY"}}
- FORBIDDEN: job_security as "High", salary as "6 LPA", why_this_career as one string, roadmap phases as strings

6b. REQUIRED_EDUCATION (limits match backend validation in recommendation_output.py):
- suggestions: array of {education_suggestion_min}–{education_suggestion_max} degree/qualification options YOU invent for this career and student
- Must be career-specific (do not repeat the same list on every career)
- Example: ["Graduation (Bachelor's)", "B.Tech in Computer Science", "MCA"]

7. ROADMAP (limits match backend validation in recommendation_output.py):
- Must be practical, not theoretical
- 4 phases: next_3_months, next_3_to_6_months, next_6_to_9_months, next_9_to_12_months
- Each phase: 1–2 actionable tasks (task_title + task_description)
- Each task_title and task_description: ONLY {roadmap_min_words}–{roadmap_max_words} words (short phrase, never a paragraph)
- Example description: "Complete online Excel course focused on data analysis and charts" (11 words)
- Focus on projects, internships, portfolio, real-world exposure
- NO repeated roadmap across careers

8. CONSISTENCY:
- Skills in explanation MUST match required_skills
- Roadmap must reflect those skills

9. EASY_DECISION_MAKING (limits match backend validation in services.ai.config):
- Exactly {easy_decision_count} items (no more, no less)
- Compare ONLY the first {easy_decision_career_count} careers in top_suggestions (rank #1 and #2)
- Each item: title (use exactly one of these four) + career_name (must be one of those two). No reason field.
- Titles (pick {easy_decision_count} different ones): "Best for quick start", "Best for high salary", "Best long term bet", "Most stable career"
- Assign each title to the career that genuinely wins that angle (salary, speed to employability, stability, long-term growth)
- Both top-two careers must appear at least once across the {easy_decision_count} items

10. OUTPUT (limits match backend validation in services.ai.config and recommendation_output.py):
- Exactly {top_suggestion_count} top_suggestions — three different careers YOU select for this student
- Each career_name must appear ONLY ONCE (never duplicate the same career twice)
- career_name must be a specific job/career title (e.g. "Data Analyst", "UX Designer"), not a domain label
- match_percentage: realistic 60–95, ranked highest first within your output
- ai_insight: one fluent {ai_insight_min_words}–{ai_insight_max_words} word sentence (never append bullet fragments after "because")

FINAL RULE:
Return ONLY valid JSON. No explanation. No extra text. No markdown code fences.

JSON SHAPE EXAMPLE (structure only — personalize all values):
{json_shape_example}
"""

_JSON_SHAPE_EXAMPLE = """{
  "top_suggestions": [
    {
      "career_name": "Data Analyst",
      "match_percentage": 88,
      "ai_insight": "Your analytical mindset and curiosity for patterns align strongly with data storytelling roles in growing firms.",
      "why_this_career": ["Strong logic fits analytics", "Enjoys structured problem solving"],
      "required_skills": ["Excel", "SQL", "Python basics"],
      "required_education": {"suggestions": ["B.Sc Statistics", "B.Tech IT"]},
      "career_factors": {
        "salary": {"average": "5-8 LPA", "growth_rate": "10% YoY"},
        "job_security": {"level": "Medium", "description": "Steady hiring in metros"},
        "learning_curve": {"level": "Moderate", "description": "Tool practice over six months"},
        "risk_level": "Medium",
        "skill_match": 84
      },
      "career_roadmap": {
        "next_3_months": [{"task_title": "Learn SQL fundamentals", "task_description": "Complete beginner SQL course with weekly practice queries"}],
        "next_3_to_6_months": [{"task_title": "Build portfolio project", "task_description": "Analyze public dataset and publish dashboard on GitHub"}],
        "next_6_to_9_months": [{"task_title": "Internship or freelance", "task_description": "Apply analytics skills on real business dataset for client"}],
        "next_9_to_12_months": [{"task_title": "Interview preparation", "task_description": "Practice case studies and mock interviews for analyst roles"}]
      }
    }
  ],
  "easy_decision_making": [
    {"title": "Best for quick start", "career_name": "Data Analyst"},
    {"title": "Best for high salary", "career_name": "Product Manager"},
    {"title": "Best long term bet", "career_name": "Data Analyst"}
  ]
}"""

RETRY_FORMAT_REMINDER = """RETRY — fix JSON formatting only:
- Return a single JSON object with keys top_suggestions and easy_decision_making only.
- job_security and learning_curve must be objects with level and description.
- salary must be an object with average and growth_rate string fields.
- why_this_career and required_skills must be arrays of strings.
- career_roadmap must include all four phase keys with task objects.
- No markdown, no commentary, no extra keys at the root."""


def _escape_langchain_template(text: str) -> str:
    """Double braces so ChatPromptTemplate treats JSON examples as literals."""
    return text.replace("{", "{{").replace("}", "}}")

USER_PROMPT = """INPUT DATA:

student_signals:
{student_signals}

Output JSON schema:
{output_shape}

{format_reminder}
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
    ).partial(output_shape=output_shape, format_reminder="")


def format_prompt_inputs(*, student_signals: dict[str, Any]) -> dict[str, str]:
    """Only assessment signals go to Groq — no DB career catalog."""
    return {
        "student_signals": json.dumps(
            student_signals,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        ),
    }
