from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from internship_generation.constants.internship_generation_constants import (
    OVERVIEW_MAX_WORDS,
    OVERVIEW_MIN_WORDS,
    OVERVIEW_TARGET_MAX_WORDS,
    OVERVIEW_TARGET_MIN_WORDS,
    RESPONSIBILITIES_MAX,
    RESPONSIBILITIES_MIN,
    SKILLS_MAX,
    SKILLS_MIN,
)

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

FIELD RULES

internship_title
- Professional internship title inferred from the employer's overview
- Examples: Software Development Intern, Python Developer Intern, Data Analyst Intern
- Avoid hype titles (no Best Internship, Rockstar Intern, Super Developer, Ninja Engineer)

about_internship
- {OVERVIEW_TARGET_MIN_WORDS}-{OVERVIEW_TARGET_MAX_WORDS} words (target), {OVERVIEW_MIN_WORDS}-{OVERVIEW_MAX_WORDS} words (allowed range)
- Write naturally in simple English — professional and student friendly
- Explain what interns will work on, main learning opportunity, and who should apply
- Do NOT repeat key_responsibilities items or skills
- Avoid marketing buzzwords (no industry-leading, world-class, cutting-edge, transformative, revolutionary, dynamic team, fast-paced environment, best-in-class)
- Only infer details reasonably supported by the employer overview — do not invent salary, benefits, remote work, office facilities, company culture, or technology not mentioned

key_responsibilities
- {RESPONSIBILITIES_MIN}-{RESPONSIBILITIES_MAX} short, action-oriented, practical responsibilities
- No duplicates

skills
- {SKILLS_MIN}-{SKILLS_MAX} practical skills relevant to this internship
- Only include skills that can be reasonably inferred from the overview
- No duplicates

STRICT VALIDATION (output will be rejected if violated)
- Invalid JSON, missing fields, or empty arrays
- Duplicate key_responsibilities or skills
- about_internship outside {OVERVIEW_MIN_WORDS}-{OVERVIEW_MAX_WORDS} words
- key_responsibilities count outside {RESPONSIBILITIES_MIN}-{RESPONSIBILITIES_MAX}
- skills count outside {SKILLS_MIN}-{SKILLS_MAX}
- Placeholder text (TBD, N/A, null, <placeholder>)
- Broken text like ", ,"
- Markdown or explanations outside JSON

Previous validation feedback (fix these issues): {{validation_feedback}}
"""

USER_PROMPT = """Generate AI fields for the Future4U Post Internship form using the employer-provided details below.

about_internship: {about_internship}
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


def format_prompt_inputs(*, generation_input: dict) -> dict[str, str]:
    deadline = generation_input.get("application_deadline")
    deadline_text = "Not provided"
    if deadline is not None:
        deadline_text = str(deadline)

    return {
        "about_internship": str(generation_input.get("about_internship") or "").strip()
        or "Not provided",
        "department": str(generation_input.get("department") or "").strip() or "Not provided",
        "stipend": str(generation_input.get("stipend") or "").strip() or "Not provided",
        "duration": str(generation_input.get("duration") or "").strip() or "Not provided",
        "mode": str(generation_input.get("mode") or "").strip() or "Not provided",
        "application_deadline": deadline_text,
        "validation_feedback": str(generation_input.get("validation_feedback") or "None").strip(),
    }
