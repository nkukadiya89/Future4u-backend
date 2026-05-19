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
You will receive:
1. student_signals (JSON) — the COMPLETE student assessment from the API, including:
   - domain_category, domain, career_direction, parent_support, concerns, career_values, user_goals
   - user, is_completed, current_screen, and every item in responses (question + selected_option)
   - computed_signals (derived scores/traits; use together with the raw assessment)
2. career_slots (JSON list) — ONLY career_name per slot (no skills, degrees, or salary from backend)

GOAL:
Generate the ENTIRE response using ONLY AI reasoning from student_signals.
Every field in the output JSON must be freshly written by you for this student.

---

STRICT RULES:

1. FULL AI CONTROL (NO DB COPY):
- career_slots tell you WHICH career titles to personalize (same career_name, same order)
- Generate ALL other fields from student_signals only — never copy from any hidden database
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
- Exactly {top_suggestion_count} top_suggestions (one per career_slots entry; same career_name, preserve order)
- Each career_name must appear ONLY ONCE in top_suggestions (never duplicate the same career twice)
- match_percentage: realistic 60–95, ranked highest first within your output
- ai_insight: one fluent {ai_insight_min_words}–{ai_insight_max_words} word sentence (never append bullet fragments after "because")

FINAL RULE:
Return ONLY valid JSON. No explanation. No extra text.
"""

USER_PROMPT = """INPUT DATA:

student_signals:
{student_signals}

career_slots:
{career_slots}

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
            (
                "system",
                SYSTEM_PROMPT.format(
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
                ),
            ),
            ("human", USER_PROMPT),
        ]
    ).partial(output_shape=output_shape)


def career_slots_for_ai(career_candidates: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Only unique career titles go to the LLM — all detail fields must be AI-generated."""
    slots: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in career_candidates:
        name = str(row.get("career_name") or "").strip()
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        slots.append({"career_name": name})
        if len(slots) >= TOP_SUGGESTION_COUNT:
            break
    return slots


def format_prompt_inputs(
    *,
    student_signals: dict[str, Any],
    career_candidates: list[dict[str, Any]],
) -> dict[str, str]:
    slots = career_slots_for_ai(career_candidates)
    return {
        "student_signals": json.dumps(
            student_signals,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        ),
        "career_slots": json.dumps(
            slots,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        ),
    }
