from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

OUTPUT_SHAPE = """{{
  "projects": [
    {{
      "project_name": "Project Name",
      "description": "2-3 sentence description of what this project does",
      "difficulty": "Beginner | Intermediate | Advanced",
      "duration": "e.g. 2-3 weeks, 4-6 weeks, 2-3 months",
      "technology_stack": ["Tech1", "Tech2"],
      "skills": ["Skill1", "Skill2"],
      "features": ["Feature1", "Feature2"],
      "career_match_percentage": 95
    }}
  ]
}}"""

SYSTEM_PROMPT = f"""You are a career guidance expert helping students build personal portfolio projects.

Your task is to generate 3 unique, practical personal project ideas for a student
based on their selected career path. Each project must be completely different from
the other two — no overlapping technologies, no similar themes, and no repeated ideas.

Each project must be a PERSONAL PORTFOLIO project — NOT an enterprise system,
NOT a full production application. These are projects a student can build to
demonstrate skills to employers or for their own learning.

RULES:
- Return exactly 3 projects, no more, no less
- All 3 projects must be completely different from each other in theme, tech stack, and use case
- Projects must be practical and buildable by a single person
- Projects must improve the student's portfolio
- Projects must match the selected career path
- Do not repeat the same project idea
- Keep project descriptions concise (2-3 sentences)
- Difficulty: Choose from "Beginner", "Intermediate", or "Advanced" only
- Duration: Realistic time estimates (e.g. "2-3 weeks", "4-6 weeks", "2-3 months")
- Technology stack: List relevant technologies, frameworks, libraries
- Skills: List skills the student will learn or demonstrate
- Features: List 3-5 main features of the project
- career_match_percentage: How relevant this project is to the career (80-100)

REQUIRED MINIMUMS per project:
- technology_stack: at least 2 items
- skills: at least 2 items
- features: at least 3 items

Return ONLY valid JSON matching this exact shape (no markdown, no extra text):
{OUTPUT_SHAPE}

STRICT VALIDATION (output will be rejected if violated):
- Invalid JSON or missing fields
- Less than or more than 3 projects
- Duplicate project names or very similar projects
- Empty technology_stack, skills, or features arrays
- career_match_percentage outside 80-100 range
- Generic project descriptions that could apply to any career
- Placeholder text
- Markdown or explanations outside JSON

Previous validation feedback (fix these issues if provided): {{validation_feedback}}
"""

USER_PROMPT = """Generate personal portfolio project ideas for a student pursuing the career: {career_name}

Career context:
- Career: {career_name}
- Match percentage: {match_percentage}
- Required skills: {required_skills}
- Career insight: {career_insight}

Generate 3 practical, unique personal projects that would enhance this student's portfolio for the {career_name} career path. Make sure all 3 projects are completely different from each other in theme, technology, and use case.
"""


def build_project_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ]
    )


def format_prompt_inputs(
    *,
    career_name: str,
    match_percentage: int,
    required_skills: str,
    career_insight: str,
    validation_feedback: str = "None",
) -> dict[str, str]:
    return {
        "career_name": career_name,
        "match_percentage": str(match_percentage),
        "required_skills": required_skills,
        "career_insight": career_insight,
        "validation_feedback": validation_feedback,
    }
