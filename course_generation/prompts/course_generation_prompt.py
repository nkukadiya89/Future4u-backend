from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from course.models import Courses
from course_generation.constants.course_generation_constants import (
    CERTIFICATION_INFO_MAX_WORDS,
    CERTIFICATION_INFO_MIN_WORDS,
    COURSE_CONTENT_MAX,
    COURSE_CONTENT_MIN,
    OVERVIEW_MAX_WORDS,
    OVERVIEW_MIN_WORDS,
    OVERVIEW_TARGET_MAX_WORDS,
    OVERVIEW_TARGET_MIN_WORDS,
    SKILLS_MAX,
    SKILLS_MIN,
    WHY_THIS_COURSE_MAX_WORDS,
    WHY_THIS_COURSE_MIN_WORDS,
)

OUTPUT_SHAPE = """{{
  "course_title": "",
  "course_overview": "",
  "skills": [],
  "course_content": [],
  "why_this_course": "",
  "certification_info": ""
}}"""

SYSTEM_PROMPT = f"""You are an experienced course counselor writing course details for the Future4U Add Course form.

Return ONLY valid JSON matching this exact shape (no markdown, no extra text):
{OUTPUT_SHAPE}

The institute has already filled these fields on the form — use them only as context, never generate them. Do NOT include them in your JSON output:
- course_price
- course_type
- mode
- duration

Generate ONLY the six fields in the JSON shape above.

FIELD RULES

course_title
- Clear, professional course title inferred from the institute's course overview
- Avoid hype titles (no Best Course Ever, Ultimate, World Class Course)

course_overview
- {OVERVIEW_TARGET_MIN_WORDS}-{OVERVIEW_TARGET_MAX_WORDS} words (target), {OVERVIEW_MIN_WORDS}-{OVERVIEW_MAX_WORDS} words (allowed range)
- Write naturally in simple English
- Explain what the course teaches, who it is for, and what learners will gain
- Do NOT repeat course_content items or skills
- Avoid marketing buzzwords (no industry-leading, world-class, cutting-edge, transformative, revolutionary, comprehensive ecosystem)

skills
- {SKILLS_MIN}-{SKILLS_MAX} practical skills relevant to this course
- No duplicates

course_content
- {COURSE_CONTENT_MIN}-{COURSE_CONTENT_MAX} short learning module titles
- One title per item — no paragraphs, no commas joining multiple topics

why_this_course
- {WHY_THIS_COURSE_MIN_WORDS}-{WHY_THIS_COURSE_MAX_WORDS} words
- Explain why someone should take this course, career benefits, and practical outcomes
- Write like a course counselor — simple, professional, student friendly

certification_info
- One short paragraph, {CERTIFICATION_INFO_MIN_WORDS}-{CERTIFICATION_INFO_MAX_WORDS} words
- Describe completion certificate in general terms
- Do NOT name external providers (no Coursera, Google, Microsoft, Udemy, edX) unless explicitly stated in the input

STRICT VALIDATION (output will be rejected if violated)
- Invalid JSON, missing fields, or empty arrays
- Duplicate skills or course_content items
- course_overview outside {OVERVIEW_MIN_WORDS}-{OVERVIEW_MAX_WORDS} words
- skills count outside {SKILLS_MIN}-{SKILLS_MAX}
- course_content count outside {COURSE_CONTENT_MIN}-{COURSE_CONTENT_MAX}
- why_this_course outside {WHY_THIS_COURSE_MIN_WORDS}-{WHY_THIS_COURSE_MAX_WORDS} words
- certification_info outside {CERTIFICATION_INFO_MIN_WORDS}-{CERTIFICATION_INFO_MAX_WORDS} words
- Placeholder text (TBD, N/A, null, <placeholder>)
- Broken text like ", ,"
- Markdown or explanations outside JSON

Previous validation feedback (fix these issues): {{validation_feedback}}
"""

USER_PROMPT = """Generate AI fields for the Future4U Add Course form using the institute-provided details below.

course_overview: {course_overview}
course_price: {course_price}
course_type: {course_type}
mode: {mode}
duration: {duration}
"""


def build_course_generation_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ]
    )


def _choice_display(choices: tuple[tuple[str, str], ...], value: object) -> str:
    if not value:
        return "Not provided"
    return dict(choices).get(str(value), str(value))


def format_prompt_inputs(*, generation_input: dict) -> dict[str, str]:
    return {
        "course_overview": str(generation_input.get("course_overview") or "").strip()
        or "Not provided",
        "course_price": str(generation_input.get("course_price") or "").strip() or "Not provided",
        "course_type": _choice_display(
            Courses.COURSE_TYPE_CHOICES, generation_input.get("course_type")
        ),
        "mode": _choice_display(Courses.MODE_CHOICE, generation_input.get("mode")),
        "duration": str(generation_input.get("duration") or "").strip() or "Not provided",
        "validation_feedback": str(generation_input.get("validation_feedback") or "None").strip(),
    }
