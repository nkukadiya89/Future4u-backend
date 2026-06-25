from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from internship_job.models import Job
from job_generation.constants.job_generation_constants import (
    DESCRIPTION_MAX_WORDS,
    DESCRIPTION_MIN_WORDS,
    DESCRIPTION_SENTENCE_COUNT,
    EDUCATION_TAGS_MAX,
    EDUCATION_TAGS_MIN,
    RESPONSIBILITIES_COUNT,
    RESPONSIBILITY_ITEM_MAX_WORDS,
    RESPONSIBILITY_ITEM_MIN_WORDS,
    WHY_THIS_MATCH_MAX_WORDS,
    WHY_THIS_MATCH_MIN_WORDS,
    WHY_THIS_MATCH_SENTENCE_COUNT,
)

OUTPUT_SHAPE = """{{
  "name": "",
  "description": "",
  "responsibilities": [],
  "skills": [],
  "education_tags": [],
  "why_this_match": ""
}}"""

SYSTEM_PROMPT = f"""You are a recruiter writing job postings for the Future4U Add Job form.

Return ONLY valid JSON matching this exact shape (no markdown, no extra text):
{OUTPUT_SHAPE}

The user has already filled these fields on the form — use them only as context, never generate them. Do NOT include them in your JSON output:
- job_summary
- organization_name
- city
- salary_range
- job_type
- experience_level
- mode
- application_deadline

Generate ONLY the six fields in the JSON shape above.

FIELD RULES

name
- Realistic, professional job title inferred from job_summary
- Avoid fancy titles (no Rockstar, Ninja, Wizard)

description
- Exactly {DESCRIPTION_SENTENCE_COUNT} short sentences, {DESCRIPTION_MIN_WORDS}-{DESCRIPTION_MAX_WORDS} words total
- Write like a recruiter in simple English — brief overview of the role and who they work with
- Do NOT repeat responsibilities or skills
- Do NOT mention salary, location, job type, work mode, or application deadline

responsibilities
- Exactly {RESPONSIBILITIES_COUNT} items, each {RESPONSIBILITY_ITEM_MIN_WORDS}-{RESPONSIBILITY_ITEM_MAX_WORDS} words
- Start each item with a strong action verb
- One clear task per line — no commas joining multiple duties

skills
- 4-8 skills relevant to this specific role (infer from job_summary)

education_tags
- Array of {EDUCATION_TAGS_MIN}-{EDUCATION_TAGS_MAX} qualification labels you infer from the role and job_summary
- Use one tag when only one qualification fits; use multiple when the role accepts several paths
- Generate realistic labels for this role (e.g. degree names, diploma levels) — do not copy from a fixed template
- No duplicates

why_this_match
- Exactly {WHY_THIS_MATCH_SENTENCE_COUNT} short sentences, {WHY_THIS_MATCH_MIN_WORDS}-{WHY_THIS_MATCH_MAX_WORDS} words total
- First sentence: mention 2-3 relevant skills from the role that fit the candidate
- Second sentence: brief fit statement
- Align with the user's experience_level and job_summary when provided

TRUTHFULNESS
- Only infer what is reasonable from the user-provided context
- Do NOT invent salary, benefits, company policies, perks, location, or remote work
- Accuracy over completeness

STRICT VALIDATION (output will be rejected if violated)
- Invalid JSON, empty skills/responsibilities/why_this_match, or empty education_tags entries
- Duplicate responsibilities, skills, or education_tags
- education_tags count outside {EDUCATION_TAGS_MIN}-{EDUCATION_TAGS_MAX}
- description not exactly {DESCRIPTION_SENTENCE_COUNT} sentences, or outside {DESCRIPTION_MIN_WORDS}-{DESCRIPTION_MAX_WORDS} words
- responsibilities count != {RESPONSIBILITIES_COUNT}, or any item outside {RESPONSIBILITY_ITEM_MIN_WORDS}-{RESPONSIBILITY_ITEM_MAX_WORDS} words
- why_this_match not exactly {WHY_THIS_MATCH_SENTENCE_COUNT} sentences, or outside {WHY_THIS_MATCH_MIN_WORDS}-{WHY_THIS_MATCH_MAX_WORDS} words
- Placeholder text (TBD, N/A, null, <placeholder>)
- Broken text like ", ,"
- Missing fields
- Write in plain, direct recruiter language

Previous validation feedback (fix these issues): {{validation_feedback}}
"""

USER_PROMPT = """Generate AI fields for the Future4U Add Job form using the user-provided details below.

job_summary: {job_summary}
organization_name: {organization_name}
city: {city}
salary_range: {salary_range}
job_type: {job_type}
experience_level: {experience_level}
mode: {mode}
application_deadline: {application_deadline}
"""


def build_job_generation_prompt() -> ChatPromptTemplate:
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
    deadline = generation_input.get("application_deadline")
    deadline_text = str(deadline).strip() if deadline else "Not provided"
    city = generation_input.get("city")
    city_text = city.name if city is not None else "Not provided"
    return {
        "job_summary": str(generation_input.get("job_summary") or "").strip() or "Not provided",
        "organization_name": str(generation_input.get("organization_name") or "").strip()
        or "Not provided",
        "city": city_text,
        "salary_range": str(generation_input.get("salary_range") or "").strip() or "Not provided",
        "job_type": _choice_display(Job.JOB_TYPE_CHOICE, generation_input.get("job_type")),
        "experience_level": _choice_display(
            Job.EXPERIENCE_CHOICES, generation_input.get("experience_level")
        ),
        "mode": _choice_display(Job.MODE_CHOICES, generation_input.get("mode")),
        "application_deadline": deadline_text,
        "validation_feedback": str(generation_input.get("validation_feedback") or "None").strip(),
    }
