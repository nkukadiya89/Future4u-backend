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

# Output shape shown to the LLM — AI only generates these 5 fields.
# Goes through .format() once (constants), then LangChain template parsing.
# Quadruple braces survive both passes as literal { } in the final prompt.
_OUTPUT_SHAPE = (
    "{{{{\n"
    '  "name": "",\n'
    '  "description": "",\n'
    '  "responsibilities": [],\n'
    '  "skills": [],\n'
    '  "education_tags": [],\n'
    '  "why_this_match": ""\n'
    "}}}}"
)

# Build the system prompt as a plain string (no f-string) so that
# LangChain's {variable} placeholders are preserved exactly.
# Constants are interpolated once here via .format(); LangChain variables
# use single braces and will be filled at invoke() time.
SYSTEM_PROMPT = (
    "You are a recruiter writing job postings for the Future4U Add Job form.\n\n"
    "Return ONLY valid JSON matching this exact shape (no markdown, no extra text):\n"
    + _OUTPUT_SHAPE
    + "\n\n"
    "The user has already filled these fields on the form — use them only as context, "
    "never generate them. Do NOT include them in your JSON output:\n"
    "- job_title\n"
    "- job_overview\n"
    "- company_name\n"
    "- company_website\n"
    "- company_about_us\n"
    "- city\n"
    "- salary_range\n"
    "- job_type\n"
    "- experience_level\n"
    "- mode\n"
    "- application_deadline\n\n"
    "Generate ONLY the six fields in the JSON shape above.\n\n"
    "--- QUALITY EXPECTATIONS ---\n\n"
    "Each generated field must feel like a real, specific job posting — not a generic template. "
    "A candidate reading it should immediately understand whether the role fits their background.\n\n"
    "Avoid:\n"
    '- Vague descriptions that could describe any job (e.g. "work with a team to deliver projects")\n'
    '- Responsibilities that are too generic (e.g. "attend meetings", "support the team")\n'
    "- Skills or education tags that don't connect to the role described\n"
    "- Padding words in description or why_this_match to hit word counts\n\n"
    "Be precise: name specific technologies, tools, and domains when the input supports them. "
    "Be honest: only include details justified by the input.\n\n"
    "--- FIELD RULES ---\n\n"
    "name\n"
    "- Realistic, professional job title (3-200 characters) inferred from job_title hint, "
    "job_overview, experience_level, and company context\n"
    "- Should match industry-standard naming (e.g. 'Junior Python Developer', 'Senior Data Analyst', 'Marketing Manager')\n"
    "- Level prefix (Junior / Senior / Lead) must align with the provided experience_level\n"
    "- If the user provided a job_title hint, refine and professionalize it — do NOT copy it verbatim\n"
    "- Avoid vague titles ('Developer', 'Associate') and hype titles (no Rockstar, Ninja, Wizard, Guru)\n"
    "- Do NOT include salary, location, or company name in the title\n\n"
    "description\n"
    "- Exactly {description_sentence_count} short sentences, "
    "{description_min_words}-{description_max_words} words total\n"
    "- Write like a recruiter in simple English — brief overview of the role and who they work with\n"
    "- First sentence: what the role is about and who they'll work with\n"
    "- Second sentence: what the organization does or the team's focus, incorporating context from "
    "company_about_us if available\n"
    "- Be concise — every word should add value\n"
    "- Do NOT repeat responsibilities or skills\n"
    "- Do NOT mention salary, location, job type, work mode, or application deadline\n\n"
    "responsibilities\n"
    "- Exactly {responsibilities_count} items, each "
    "{responsibility_item_min_words}-{responsibility_item_max_words} words\n"
    "- Start each item with a strong action verb "
    "(Build, Design, Develop, Analyze, Lead, Manage, Create, Implement, Optimize)\n"
    "- Each responsibility should describe a concrete, measurable task — not a broad area\n"
    '- Good: "Design and implement RESTful APIs for the client dashboard"\n'
    '- Poor: "Work on backend development" or "Help the development team"\n'
    "- One clear task per line — no commas joining multiple duties\n\n"
    "skills\n"
    "- 4-8 skills relevant to this specific role (infer from job_overview, "
    "company context, and experience_level)\n"
    "- Every skill should connect to at least one listed responsibility\n"
    '- Prefer specific technologies over broad categories ("React" over '
    '"Frontend Development", "AWS" over "Cloud Computing")\n\n'
    "education_tags\n"
    "- Array of {education_tags_min}-{education_tags_max} qualification labels "
    "you infer from the role and job_overview\n"
    "- Use one tag when only one qualification fits; use multiple when the role accepts several paths\n"
    '- Generate realistic, specific labels for this role (e.g. "B.Tech in Computer Science", '
    '"BCA", "MBA in Marketing") — do not copy from a fixed template or use generic '
    '"Bachelor\'s Degree" without a field\n'
    "- No duplicates\n"
    "- Tie each tag to what makes sense for the role (technical roles → relevant tech degrees, "
    "marketing roles → relevant commerce/marketing degrees)\n\n"
    "why_this_match\n"
    "- Exactly {why_this_match_sentence_count} short sentences, "
    "{why_this_match_min_words}-{why_this_match_max_words} words total\n"
    "- First sentence: name 2-3 specific skills from the role that align with a "
    "hypothetical candidate's profile\n"
    "- Second sentence: brief fit statement about why this role suits someone with those skills\n"
    "- Make it sound personalized, not templated — vary the sentence structure\n"
    "- Align with the user's experience_level and job_overview when provided\n\n"
    "--- TRUTHFULNESS ---\n"
    "- Only infer what is reasonable from the user-provided context\n"
    "- Do NOT invent salary, benefits, company policies, perks, location, or remote work\n"
    "- Do NOT invent specific tools, frameworks, or technologies not mentioned or "
    "strongly implied by the input\n"
    "- Accuracy over completeness — better to have 4 well-chosen skills than 8 mismatched ones\n\n"
    "--- STRICT VALIDATION (output will be rejected if violated) ---\n"
    "- Invalid JSON, empty skills/responsibilities/why_this_match, or empty education_tags entries\n"
    "- Duplicate responsibilities, skills, or education_tags\n"
    "- education_tags count outside {education_tags_min}-{education_tags_max}\n"
    "- description not exactly {description_sentence_count} sentences, or outside "
    "{description_min_words}-{description_max_words} words\n"
    "- responsibilities count != {responsibilities_count}, or any item outside "
    "{responsibility_item_min_words}-{responsibility_item_max_words} words\n"
    "- why_this_match not exactly {why_this_match_sentence_count} sentences, or outside "
    "{why_this_match_min_words}-{why_this_match_max_words} words\n"
    "- Placeholder text (TBD, N/A, null, <placeholder>)\n"
    '- Broken text like ", ," or empty brackets\n'
    "- Missing fields\n"
    "- Write in plain, direct recruiter language\n"
    "- Skills that have no connection to any listed responsibility\n"
    '- Generic education tags (prefer "B.Tech in Computer Science" over "Bachelor\'s Degree")\n\n'
    "Previous validation feedback (fix these issues): {validation_feedback}"
).format(
    description_sentence_count=DESCRIPTION_SENTENCE_COUNT,
    description_min_words=DESCRIPTION_MIN_WORDS,
    description_max_words=DESCRIPTION_MAX_WORDS,
    responsibilities_count=RESPONSIBILITIES_COUNT,
    responsibility_item_min_words=RESPONSIBILITY_ITEM_MIN_WORDS,
    responsibility_item_max_words=RESPONSIBILITY_ITEM_MAX_WORDS,
    education_tags_min=EDUCATION_TAGS_MIN,
    education_tags_max=EDUCATION_TAGS_MAX,
    why_this_match_sentence_count=WHY_THIS_MATCH_SENTENCE_COUNT,
    why_this_match_min_words=WHY_THIS_MATCH_MIN_WORDS,
    why_this_match_max_words=WHY_THIS_MATCH_MAX_WORDS,
    # LangChain variables — re-insert as {variable} after .format() replaces constants
    validation_feedback="{validation_feedback}",
)

USER_PROMPT = (
    "Generate AI fields for the Future4U Add Job form using the user-provided details below.\n\n"
    "job_title: {job_title}\n"
    "job_overview: {job_overview}\n"
    "--- Company Context ---\n"
    "Company Name: {company_name}\n"
    "Website: {company_website}\n"
    "About Company: {company_about_us}\n"
    "---\n"
    "city: {city}\n"
    "salary_range: {salary_range}\n"
    "job_type: {job_type}\n"
    "experience_level: {experience_level}\n"
    "mode: {mode}\n"
    "application_deadline: {application_deadline}\n"
)


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
        "job_title": str(generation_input.get("job_title") or "").strip()
        or "Not provided",
        "job_overview": str(generation_input.get("job_overview") or "").strip()
        or "Not provided",
        "company_name": str(generation_input.get("company_name") or "").strip()
        or "Not provided",
        "company_website": str(generation_input.get("company_website") or "").strip()
        or "Not provided",
        "company_about_us": str(generation_input.get("company_about_us") or "").strip()
        or "Not provided",
        "city": city_text,
        "salary_range": _format_salary(generation_input),
        "job_type": _choice_display(
            Job.JOB_TYPE_CHOICE, generation_input.get("job_type")
        ),
        "experience_level": _choice_display(
            Job.EXPERIENCE_CHOICES, generation_input.get("experience_level")
        ),
        "mode": _choice_display(Job.MODE_CHOICES, generation_input.get("mode")),
        "application_deadline": deadline_text,
        "validation_feedback": str(
            generation_input.get("validation_feedback") or "None"
        ).strip(),
    }
