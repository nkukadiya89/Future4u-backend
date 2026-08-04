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
    SKILLS_ITEM_MAX_WORDS,
    SKILLS_MAX,
    SKILLS_MIN,
    WHY_THIS_COURSE_MAX_WORDS,
    WHY_THIS_COURSE_MIN_WORDS,
    WHY_THIS_COURSE_TARGET_MAX_WORDS,
    WHY_THIS_COURSE_TARGET_MIN_WORDS,
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
- provider_type
- course_provider

Generate ONLY the six fields in the JSON shape above. Every value must be written fresh from the institute-provided details in the user message. Never copy placeholder or example text from these instructions.

Write specific, course-relevant content — no generic templates, vague phrases, or invented details. Name specific tools, technologies, or domains when the input supports them.

--- FIELD RULES ---

course_title
- Clear, professional course title that precisely reflects the course content
- If the user provided a course_title hint, refine and professionalize it — do NOT copy it verbatim; keep the subject the same
- If no course_title hint is provided, generate a suitable title from the course_overview
- Avoid hype titles (no Best Course Ever, Ultimate, World Class Course)
- Good: "Advanced Data Analytics with Python" | "Full-Stack Web Development with React & Django"
- Poor: "Computer Course" | "Skill Development Program"

course_overview
- {OVERVIEW_MIN_WORDS}–{OVERVIEW_MAX_WORDS} words (target {OVERVIEW_TARGET_MIN_WORDS}–{OVERVIEW_TARGET_MAX_WORDS})
- ONE paragraph only — no bullet points, no line breaks, no second paragraph
- Cover: what the course teaches → key learning outcomes → who it suits
- Mention specific tools/technologies/domains from the input
- Do NOT repeat course_content module titles or skills verbatim
- Do NOT use marketing buzzwords (industry-leading, world-class, cutting-edge, transformative, revolutionary, comprehensive ecosystem)

skills
- {SKILLS_MIN}-{SKILLS_MAX} short skill tags for a "Skills You Will Learn" pill UI
- Each skill: 1-{SKILLS_ITEM_MAX_WORDS} words, concise label only (no sentences, no parenthetical text)
- Derive from the course overview and form context; no duplicates

course_content
- {COURSE_CONTENT_MIN}-{COURSE_CONTENT_MAX} short learning module titles as strings
- One title per item, reads like a real course module (e.g. "Introduction to Data Structures")
- Progress from fundamentals to advanced where natural; no duplicates

why_this_course
- {WHY_THIS_COURSE_MIN_WORDS}–{WHY_THIS_COURSE_MAX_WORDS} words (target {WHY_THIS_COURSE_TARGET_MIN_WORDS}–{WHY_THIS_COURSE_TARGET_MAX_WORDS})
- ONE paragraph only
- Explain the key benefit of this specific course and career/skill outcomes
- Do NOT repeat course_overview, module titles, or skills verbatim
- Do NOT use marketing buzzwords or promise guaranteed jobs/salaries/placements

certification_info
- {CERTIFICATION_INFO_MIN_WORDS}-{CERTIFICATION_INFO_MAX_WORDS} words, one paragraph
- Describe what the completion certificate demonstrates or validates
- Do NOT name external providers (Coursera, Google, Microsoft, Udemy, edX) unless explicitly stated in the input

Previous validation feedback (fix these issues if provided): {{validation_feedback}}
"""

USER_PROMPT = """Generate AI fields for the Future4U Add Course form using the institute-provided details below.

course_title: {course_title}
course_overview: {course_overview}
course_price: {course_price}
course_type: {course_type}
mode: {mode}
duration: {duration}
provider_type: {provider_type}
course_provider: {course_provider}
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
        return ""
    return dict(choices).get(str(value), str(value))


def format_prompt_inputs(*, generation_input: dict) -> dict[str, str]:
    # Resolve course_provider name from profile
    course_provider = generation_input.get("course_provider")
    if course_provider:
        name = None
        if hasattr(course_provider, "institute_profile"):
            name = getattr(course_provider.institute_profile, "institute_name", None)
        if not name and hasattr(course_provider, "school_college_profile"):
            name = getattr(
                course_provider.school_college_profile, "institute_name", None
            )
        course_provider_str = (
            name or getattr(course_provider, "full_name", None) or str(course_provider)
        )
    else:
        course_provider_str = ""

    return {
        "course_title": str(generation_input.get("course_title") or "").strip()
        or "Not provided",
        "course_overview": str(generation_input.get("course_overview") or "").strip(),
        "course_price": str(generation_input.get("course_price") or "").strip(),
        "course_type": _choice_display(
            Courses.COURSE_TYPE_CHOICES, generation_input.get("course_type")
        ),
        "mode": _choice_display(Courses.MODE_CHOICE, generation_input.get("mode")),
        "duration": str(generation_input.get("duration") or "").strip(),
        "provider_type": _choice_display(
            Courses.PROVIDER_TYPE_CHOICES, generation_input.get("provider_type")
        ),
        "course_provider": course_provider_str,
        "validation_feedback": str(
            generation_input.get("validation_feedback") or ""
        ).strip(),
    }
