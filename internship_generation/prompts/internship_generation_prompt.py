from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from internship_generation.constants.internship_generation_constants import (
    ABOUT_INTERNSHIP_MAX_WORDS,
    ABOUT_INTERNSHIP_MIN_WORDS,
    ABOUT_INTERNSHIP_TARGET_MAX_WORDS,
    ABOUT_INTERNSHIP_TARGET_MIN_WORDS,
    RESPONSIBILITIES_MAX,
    RESPONSIBILITIES_MIN,
    SKILLS_MAX,
    SKILLS_MIN,
)
from internship_job.models import Internship

OUTPUT_SHAPE = """{{
  "internship_title": "",
  "about_internship": "",
  "key_responsibilities": [],
  "skills": []
}}"""

SYSTEM_PROMPT = f"""You are an experienced recruiter writing internship details for the Future4U Post Internship form.

Return ONLY valid JSON matching this exact shape (no markdown, no extra text):
{OUTPUT_SHAPE}

The employer has already filled these fields on the form — use them only as context, never generate them. Do NOT include them in your JSON output:
- department
- stipend
- duration
- mode
- application_deadline

Generate ONLY the four fields in the JSON shape above.

Write specific, role-relevant content — no generic templates, vague phrases, or invented details.

--- FIELD RULES ---

internship_title
- Professional internship title that clearly communicates the role and domain
- Format: "[Domain/Area] Intern" — e.g. "Software Development Intern", "Digital Marketing Intern", "Data Analyst Intern"
- Avoid vague titles ("Intern", "Trainee") and hype titles

about_internship
- {ABOUT_INTERNSHIP_MIN_WORDS}–{ABOUT_INTERNSHIP_MAX_WORDS} words (target {ABOUT_INTERNSHIP_TARGET_MIN_WORDS}–{ABOUT_INTERNSHIP_TARGET_MAX_WORDS})
- EXACTLY ONE paragraph — no blank lines or line breaks between sentences
- Cover in order: internship role → primary work area → what intern learns/contributes → who it suits
- Professional, student-friendly, simple English
- Do NOT repeat key_responsibilities or skills verbatim, list technologies one by one, or mention stipend/benefits
- Do NOT use marketing buzzwords (industry-leading, world-class, cutting-edge, revolutionary, dynamic environment, fast-paced, best-in-class)

key_responsibilities
- {RESPONSIBILITIES_MIN}-{RESPONSIBILITIES_MAX} short, action-oriented, practical responsibilities
- Each item: concrete task starting with a strong action verb (Develop, Design, Write, Analyze, Create, Test, Build, Research)
- No vague items ("Assist with testing"), no duplicates

skills
- {SKILLS_MIN}-{SKILLS_MAX} practical skills, each connected to at least one responsibility
- Specific tools/technologies over broad categories ("Python" over "Programming")
- No duplicates

Previous validation feedback (fix these issues): {{validation_feedback}}
"""

USER_PROMPT = """Generate AI fields for the Future4U Post Internship form using the employer-provided details below.

internship_title (employer input): {internship_title}
internship_overview (employer input): {internship_overview}
department: {department}
stipend: {stipend}
duration: {duration}
mode: {mode}
application_deadline: {application_deadline}
"""


def build_internship_generation_prompt() -> ChatPromptTemplate:
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
    deadline_text = "Not provided"
    if deadline is not None:
        deadline_text = str(deadline)

    return {
        "internship_title": str(generation_input.get("internship_title") or "").strip()
        or "Not provided",
        "internship_overview": str(
            generation_input.get("internship_overview") or ""
        ).strip()
        or "Not provided",
        "department": str(generation_input.get("department") or "").strip()
        or "Not provided",
        "stipend": str(generation_input.get("stipend") or "").strip() or "Not provided",
        "duration": str(generation_input.get("duration") or "").strip()
        or "Not provided",
        "mode": _choice_display(Internship.MODE_CHOICE, generation_input.get("mode")),
        "application_deadline": deadline_text,
        "validation_feedback": str(
            generation_input.get("validation_feedback") or "None"
        ).strip(),
    }
