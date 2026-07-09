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

Generate ONLY the six fields in the JSON shape above. Every value must be written fresh from the institute-provided details in the user message. Never copy placeholder or example text from these instructions.

--- QUALITY EXPECTATIONS ---

Each generated field must feel specific to the institute's course, not generic. A reader should be able to identify this course from the generated fields alone. Avoid:
- Vague statements that could apply to any course (e.g. "learn valuable skills", "gain practical knowledge")
- Padding sentences that add word count without substance
- Copying phrases from the instructions or examples

The output must be concrete: name specific tools, technologies, domains, or skills the user provided. Use natural, varied language — do not repeat the same sentence structures across fields.

--- FIELD RULES ---

course_title
- Clear, professional course title that precisely reflects the course content
- Must be specific enough to distinguish this course from generic offerings
- Avoid hype titles (no Best Course Ever, Ultimate, World Class Course)
- Good: "Advanced Data Analytics with Python" | "Full-Stack Web Development with React & Django"
- Poor: "Computer Course" | "Skill Development Program"

course_overview
- Target: {OVERVIEW_TARGET_MIN_WORDS}-{OVERVIEW_TARGET_MAX_WORDS} words. Hard maximum: {OVERVIEW_MAX_WORDS} words. Minimum: {OVERVIEW_MIN_WORDS} words.
- Write ONE concise paragraph only — no bullet points, no line breaks, no second paragraph
- Cover three things in that single paragraph: what the course teaches → key learning outcomes → who it is suitable for
- Mention specific tools, technologies, or domains when provided in the input
- Do NOT repeat course_content module titles or skills verbatim
- Do NOT use marketing buzzwords (no industry-leading, world-class, cutting-edge, transformative, revolutionary, comprehensive ecosystem)
- Keep language plain and mobile-friendly — short sentences, no jargon
- REJECT AND REGENERATE if: more than {OVERVIEW_MAX_WORDS} words, more than one paragraph, repeats skills or content module titles, or contains marketing buzzwords

skills
- {SKILLS_MIN}-{SKILLS_MAX} short skill tags for a "Skills You Will Learn" pill UI
- Each skill is 1-{SKILLS_ITEM_MAX_WORDS} words — concise labels only (no sentences, no descriptions, no examples in parentheses)
- Derive every skill from the institute course overview and form context
- Skills should be specific and scannable: "Python", "Data Visualization", "Circuit Design" — not sentences or paragraphs
- No duplicates

course_content
- {COURSE_CONTENT_MIN}-{COURSE_CONTENT_MAX} short learning module titles as strings
- One title per item — no paragraphs, no commas joining multiple topics
- Each title should read like a real course module (e.g. "Introduction to Data Structures", "Advanced SQL Queries")
- Derive every module title from the institute course overview and form context
- Progress from fundamentals to advanced where natural

why_this_course
- Target: {WHY_THIS_COURSE_TARGET_MIN_WORDS}-{WHY_THIS_COURSE_TARGET_MAX_WORDS} words. Hard maximum: {WHY_THIS_COURSE_MAX_WORDS} words. Minimum: {WHY_THIS_COURSE_MIN_WORDS} words.
- Write ONE short paragraph only — no bullet points, no line breaks, no second paragraph
- Explain the key benefit of this specific course and mention career or skill development outcomes
- Tie benefits back to the actual course content — do not make generic statements
- Do NOT repeat the course_overview, course_content module titles, or skills verbatim
- Do NOT use marketing buzzwords (no unlock your potential, transform your career, take the next step)
- Do NOT mention guaranteed jobs, guaranteed salaries, or guaranteed placements
- REJECT AND REGENERATE if: more than {WHY_THIS_COURSE_MAX_WORDS} words, more than one paragraph, repeats overview or skills, contains marketing language, or makes job/salary guarantees

certification_info
- One short paragraph, {CERTIFICATION_INFO_MIN_WORDS}-{CERTIFICATION_INFO_MAX_WORDS} words
- Describe the completion certificate in general but meaningful terms
- Mention what the certificate demonstrates or validates (e.g. proficiency in the subject area)
- Do NOT name external providers (no Coursera, Google, Microsoft, Udemy, edX) unless explicitly stated in the input
- Keep it realistic — do not promise industry accreditation unless the input suggests it

--- STRICT VALIDATION (output will be rejected if violated) ---
- Invalid JSON, missing fields, or empty arrays
- Duplicate skills or course_content items
- course_overview outside {OVERVIEW_MIN_WORDS}-{OVERVIEW_MAX_WORDS} words
- course_overview with more than one paragraph
- course_overview that copies two or more course_content module titles verbatim
- course_overview containing marketing buzzwords
- skills count outside {SKILLS_MIN}-{SKILLS_MAX}
- any skill longer than {SKILLS_ITEM_MAX_WORDS} words or with parenthetical text
- course_content count outside {COURSE_CONTENT_MIN}-{COURSE_CONTENT_MAX}
- why_this_course outside {WHY_THIS_COURSE_MIN_WORDS}-{WHY_THIS_COURSE_MAX_WORDS} words
- why_this_course with more than one paragraph
- why_this_course that repeats the course_overview, skills, or course_content verbatim
- why_this_course containing marketing language or job/salary guarantees
- certification_info outside {CERTIFICATION_INFO_MIN_WORDS}-{CERTIFICATION_INFO_MAX_WORDS} words
- Placeholder text (TBD, N/A, null, <placeholder>)
- Broken text like ", ," or empty brackets
- Markdown or explanations outside JSON
- Generic content that could describe any course (lacks specificity)

Previous validation feedback (fix these issues if provided): {{validation_feedback}}
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
        return ""
    return dict(choices).get(str(value), str(value))


def format_prompt_inputs(*, generation_input: dict) -> dict[str, str]:
    return {
        "course_overview": str(generation_input.get("course_overview") or "").strip(),
        "course_price": str(generation_input.get("course_price") or "").strip(),
        "course_type": _choice_display(
            Courses.COURSE_TYPE_CHOICES, generation_input.get("course_type")
        ),
        "mode": _choice_display(Courses.MODE_CHOICE, generation_input.get("mode")),
        "duration": str(generation_input.get("duration") or "").strip(),
        "validation_feedback": str(generation_input.get("validation_feedback") or "").strip(),
    }
