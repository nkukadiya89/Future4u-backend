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
- job_overview
- organization_name
- city
- salary_range
- job_type
- experience_level
- mode
- application_deadline

Generate ONLY the six fields in the JSON shape above.

--- QUALITY EXPECTATIONS ---

Each generated field must feel like a real, specific job posting — not a generic template. A candidate reading it should immediately understand whether the role fits their background.

Avoid:
- Vague descriptions that could describe any job (e.g. "work with a team to deliver projects")
- Responsibilities that are too generic (e.g. "attend meetings", "support the team")
- Skills or education tags that don't connect to the role described
- Padding words in description or why_this_match to hit word counts

Be precise: name specific technologies, tools, and domains when the input supports them. Be honest: only include details justified by the input.

--- FIELD RULES ---

name
- Realistic, professional job title inferred from job_overview and experience_level
- Should match industry-standard naming (e.g. "Junior Python Developer", "Senior Data Analyst", "Marketing Manager")
- Level prefix (Junior / Senior / Lead) must align with the provided experience_level
- Avoid vague titles ("Developer", "Associate") and hype titles (no Rockstar, Ninja, Wizard, Guru)

description
- Exactly {DESCRIPTION_SENTENCE_COUNT} short sentences, {DESCRIPTION_MIN_WORDS}-{DESCRIPTION_MAX_WORDS} words total
- Write like a recruiter in simple English — brief overview of the role and who they work with
- First sentence: what the role is about and who they'll work with
- Second sentence: what the organization does or the team's focus
- Be concise — every word should add value
- Do NOT repeat responsibilities or skills
- Do NOT mention salary, location, job type, work mode, or application deadline

responsibilities
- Exactly {RESPONSIBILITIES_COUNT} items, each {RESPONSIBILITY_ITEM_MIN_WORDS}-{RESPONSIBILITY_ITEM_MAX_WORDS} words
- Start each item with a strong action verb (Build, Design, Develop, Analyze, Lead, Manage, Create, Implement, Optimize)
- Each responsibility should describe a concrete, measurable task — not a broad area
- Good: "Design and implement RESTful APIs for the client dashboard"
- Poor: "Work on backend development" or "Help the development team"
- One clear task per line — no commas joining multiple duties

skills
- 4-8 skills relevant to this specific role (infer from job_overview)
- Every skill should connect to at least one listed responsibility
- Prefer specific technologies over broad categories ("React" over "Frontend Development", "AWS" over "Cloud Computing")

education_tags
- Array of {EDUCATION_TAGS_MIN}-{EDUCATION_TAGS_MAX} qualification labels you infer from the role and job_overview
- Use one tag when only one qualification fits; use multiple when the role accepts several paths
- Generate realistic, specific labels for this role (e.g. "B.Tech in Computer Science", "BCA", "MBA in Marketing") — do not copy from a fixed template or use generic "Bachelor's Degree" without a field
- No duplicates
- Tie each tag to what makes sense for the role (technical roles → relevant tech degrees, marketing roles → relevant commerce/marketing degrees)

why_this_match
- Exactly {WHY_THIS_MATCH_SENTENCE_COUNT} short sentences, {WHY_THIS_MATCH_MIN_WORDS}-{WHY_THIS_MATCH_MAX_WORDS} words total
- First sentence: name 2-3 specific skills from the role that align with a hypothetical candidate's profile
- Second sentence: brief fit statement about why this role suits someone with those skills
- Make it sound personalized, not templated — vary the sentence structure
- Align with the user's experience_level and job_overview when provided

--- TRUTHFULNESS ---
- Only infer what is reasonable from the user-provided context
- Do NOT invent salary, benefits, company policies, perks, location, or remote work
- Do NOT invent specific tools, frameworks, or technologies not mentioned or strongly implied by the input
- Accuracy over completeness — better to have 4 well-chosen skills than 8 mismatched ones

--- STRICT VALIDATION (output will be rejected if violated) ---
- Invalid JSON, empty skills/responsibilities/why_this_match, or empty education_tags entries
- Duplicate responsibilities, skills, or education_tags
- education_tags count outside {EDUCATION_TAGS_MIN}-{EDUCATION_TAGS_MAX}
- description not exactly {DESCRIPTION_SENTENCE_COUNT} sentences, or outside {DESCRIPTION_MIN_WORDS}-{DESCRIPTION_MAX_WORDS} words
- responsibilities count != {RESPONSIBILITIES_COUNT}, or any item outside {RESPONSIBILITY_ITEM_MIN_WORDS}-{RESPONSIBILITY_ITEM_MAX_WORDS} words
- why_this_match not exactly {WHY_THIS_MATCH_SENTENCE_COUNT} sentences, or outside {WHY_THIS_MATCH_MIN_WORDS}-{WHY_THIS_MATCH_MAX_WORDS} words
- Placeholder text (TBD, N/A, null, <placeholder>)
- Broken text like ", ," or empty brackets
- Missing fields
- Write in plain, direct recruiter language
- Skills that have no connection to any listed responsibility
- Generic education tags (prefer "B.Tech in Computer Science" over "Bachelor's Degree")

Previous validation feedback (fix these issues): {{validation_feedback}}
"""

USER_PROMPT = """Generate AI fields for the Future4U Add Job form using the user-provided details below.

job_overview: {job_overview}
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


def _format_salary(generation_input: dict) -> str:
    """Convert salary_min / salary_max (INR) to a readable string for the AI prompt."""
    salary_min = generation_input.get("salary_min")
    salary_max = generation_input.get("salary_max")

    if salary_min is None and salary_max is None:
        return "Not provided"

    def to_lpa(amount) -> str:
        lpa = float(amount) / 100_000
        # Show as integer if it's a whole number, else 1 decimal place
        return f"{lpa:.0f}" if lpa == int(lpa) else f"{lpa:.1f}"

    if salary_min is not None and salary_max is not None:
        return f"INR {to_lpa(salary_min)}-{to_lpa(salary_max)} LPA"
    if salary_min is not None:
        return f"INR {to_lpa(salary_min)} LPA (min)"
    return f"INR {to_lpa(salary_max)} LPA (max)"


def format_prompt_inputs(*, generation_input: dict) -> dict[str, str]:
    deadline = generation_input.get("application_deadline")
    deadline_text = str(deadline).strip() if deadline else "Not provided"
    city = generation_input.get("city")
    city_text = city.name if city is not None else "Not provided"
    return {
        "job_overview": str(generation_input.get("job_overview") or "").strip() or "Not provided",
        "organization_name": str(generation_input.get("organization_name") or "").strip()
        or "Not provided",
        "city": city_text,
        "salary_range": _format_salary(generation_input),
        "job_type": _choice_display(Job.JOB_TYPE_CHOICE, generation_input.get("job_type")),
        "experience_level": _choice_display(
            Job.EXPERIENCE_CHOICES, generation_input.get("experience_level")
        ),
        "mode": _choice_display(Job.MODE_CHOICES, generation_input.get("mode")),
        "application_deadline": deadline_text,
        "validation_feedback": str(generation_input.get("validation_feedback") or "None").strip(),
    }
