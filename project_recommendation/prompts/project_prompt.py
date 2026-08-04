from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


SYSTEM_PROMPT = (
    "You are a Career Portfolio Project Recommendation AI.\n\n"
    "RULES:\n"
    "1. Recommend projects a student would realistically do during an internship or practical training in the given profession — not generic software or startup ideas.\n"
    "2. Software projects only when the profession's core work IS software (e.g. Software Dev, Data Science, Cyber Security, DevOps, AI/ML, Web/Mobile Dev, Cloud, Game Dev). For all other domains, recommend field-specific practical work.\n"
    "3. Projects must be achievable at the given education level using free tools, public data, surveys, reports, or field observations — no labs, equipment, or institutional access required.\n"
    "4. Each project must be industry-specific, internship-ready, and portfolio-worthy.\n\n"
    "OUTPUT: Return EXACTLY 3 projects as a JSON object:\n"
    '{{"projects": [{{\n'
    '  "project_name": "max 8 words",\n'
    '  "short_description": "30-50 words: what the student will do",\n'
    '  "difficulty": "Beginner|Intermediate|Advanced",\n'
    '  "estimated_duration": "e.g. 2 Weeks",\n'
    '  "industry_relevance": "one sentence linking to real industry work",\n'
    '  "skills_gained": ["skill1","skill2","skill3","skill4","skill5"],\n'
    '  "portfolio_value": "one sentence on career impact",\n'
    '  "why_this_project": "max 25 words on value for internships/jobs"\n'
    "}}]}}\n\n"
    "Return ONLY valid JSON. No markdown. No extra text."
)

USER_PROMPT = (
    "Domain: {domain}\n"
    "Specialisation: {domain_category}\n"
    "Education Level: {education_level}"
)


def build_project_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])


def format_prompt_inputs(
    *,
    domain: str,
    domain_category: str,
    career_name: str = "",
    education_level: str = "",
    validation_feedback: str = "None",
) -> dict[str, str]:
    return {
        "domain": domain or "Not specified",
        "domain_category": domain_category or "Not specified",
        "education_level": education_level or "Not specified",
    }
