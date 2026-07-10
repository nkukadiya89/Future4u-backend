from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from internship_job.models import Internship
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

--- QUALITY EXPECTATIONS ---

Every internship description should feel authentic and specific to the employer's posting, not a generic template. A student reading it should have a clear picture of what they would actually do day-to-day.

Avoid:
- Vague responsibilities like "assist the team" or "support daily operations"
- Skills that don't connect to the responsibilities (every skill should be used in at least one responsibility)
- Generic phrases that could describe any internship at any company

Be honest: only include details supported by the input. If the employer didn't mention a specific technology, don't invent it.

--- FIELD RULES ---

internship_title
- Professional internship title that clearly communicates the role and domain
- Format: "[Domain/Area] Intern" — e.g. "Software Development Intern", "Digital Marketing Intern", "Data Analyst Intern"
- Avoid vague titles ("Intern", "Trainee") and hype titles (no Best Internship, Rockstar Intern, Super Developer, Ninja Engineer)

about_internship
PURPOSE: A concise, engaging overview that quickly explains what the internship offers and encourages eligible students to apply.

LENGTH:
- Minimum: {ABOUT_INTERNSHIP_MIN_WORDS} words
- Maximum: {ABOUT_INTERNSHIP_MAX_WORDS} words (HARD LIMIT — output will be REJECTED if exceeded)
- Ideal target: {ABOUT_INTERNSHIP_TARGET_MIN_WORDS}–{ABOUT_INTERNSHIP_TARGET_MAX_WORDS} words

STRUCTURE:
- Write EXACTLY ONE short paragraph — no blank lines, no line breaks between sentences
- Follow this order:
  1. Describe the internship role
  2. Mention the primary technologies or work area
  3. Explain what the intern will learn or contribute
  4. End with who the internship is suitable for

MUST INCLUDE (high level only, not verbatim from lists):
- Internship role
- Main responsibilities (briefly, not as a list)
- Learning opportunity
- Collaboration with the team
- Suitable candidate profile

WRITING STYLE:
- Professional, natural, student-friendly, easy to read, human sounding
- Simple English — avoid jargon or complex sentence structures

DO NOT:
- Repeat key_responsibilities items verbatim
- Repeat skills items verbatim
- List technologies one by one (e.g. "Python, Django, PostgreSQL, Git, Docker")
- Mention salary, stipend, benefits, or company policies
- Write more than one paragraph
- Exceed {ABOUT_INTERNSHIP_MAX_WORDS} words
- Use any of these banned phrases: industry-leading, world-class, cutting-edge, revolutionary, dynamic environment, fast-paced, best-in-class

GOOD EXAMPLE ({ABOUT_INTERNSHIP_TARGET_MIN_WORDS}–{ABOUT_INTERNSHIP_TARGET_MAX_WORDS} words, one paragraph):
"Start your software development career by working on real-world backend projects using Python and Django. This internship provides practical experience with API development, databases, debugging, and team collaboration, making it an excellent opportunity for students and recent graduates eager to strengthen their backend development skills."

BAD EXAMPLE (too long, lists everything, reads like a job spec):
"As a Software Development Intern you will build backend features for web applications using Python and Django, creating RESTful APIs that power the front-end experience. You will gain practical knowledge of database integration, write clean, maintainable code, use Git for version control, fix bugs, participate in code reviews, collaborate with teams, and work on multiple projects while learning industry best practices..."

key_responsibilities
- {RESPONSIBILITIES_MIN}-{RESPONSIBILITIES_MAX} short, action-oriented, practical responsibilities
- Each item should describe a concrete task, not a vague area (e.g. "Write and execute test cases for web applications" is good; "Assist with testing" is poor)
- Start each item with a strong action verb (Develop, Design, Write, Analyze, Create, Test, Build, Research)
- Each responsibility should feel like a real task an intern would own, not a broad area
- No duplicates

skills
- {SKILLS_MIN}-{SKILLS_MAX} practical skills relevant to this internship
- Every skill listed should connect to at least one key_responsibility — avoid filler skills
- Only include skills that can be reasonably inferred from the employer's overview
- Prefer specific technologies/tools over broad categories ("Python" over "Programming", "Adobe Photoshop" over "Design")
- No duplicates

--- STRICT VALIDATION (output will be REJECTED if any rule is violated) ---
- Invalid JSON, missing fields, or empty arrays
- Duplicate key_responsibilities or skills
- about_internship word count outside {ABOUT_INTERNSHIP_MIN_WORDS}–{ABOUT_INTERNSHIP_MAX_WORDS} words
- about_internship has more than one paragraph (blank line between sentences = instant rejection)
- about_internship copies key_responsibilities or skills verbatim
- key_responsibilities count outside {RESPONSIBILITIES_MIN}-{RESPONSIBILITIES_MAX}
- skills count outside {SKILLS_MIN}-{SKILLS_MAX}
- Placeholder text (TBD, N/A, null, <placeholder>)
- Broken text like ", ," or empty brackets
- Markdown or explanations outside JSON
- Banned marketing phrases in about_internship
- Generic responsibilities that could apply to any internship (lacks specificity)
- Skills that do not map to any listed responsibility

Previous validation feedback (fix these issues): {{validation_feedback}}
"""

USER_PROMPT = """Generate AI fields for the Future4U Post Internship form using the employer-provided details below.

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
