"""AI service for resume summary enhancement."""

from __future__ import annotations

import logging

from resume_builder.resume_services.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)


def _call_groq(prompt: str, max_tokens: int) -> str:
    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def _call_ai(prompt: str, max_tokens: int) -> str:
    if not GROQ_API_KEY:
        raise ValueError("No AI provider configured. Set GROQ_API_KEY in .env")

    try:
        result = _call_groq(prompt, max_tokens)
        logger.info("AI summary generated via Groq")
        return result
    except Exception as exc:
        logger.error("Groq failed: %s", exc)
        raise ValueError(f"AI provider failed. Last error: {exc}") from exc


def enhance_fresher_summary(data: dict) -> str:
    """Generate an ATS-optimized objective for a fresher resume."""
    pi = data["personal_info"]
    cd = data["career_direction"]
    skills = ", ".join(data["skills"]["technical"] + data["skills"]["soft"])
    projects = "; ".join(p["title"] for p in data["projects"])

    prompt = f"""You are an expert resume writer specializing in fresher/entry-level resumes.

Write a sharp, ATS-optimized professional objective for {pi['name']}.

Context:
- Target Role: {cd['target_role']}
- Target Industry: {cd['target_industry']}
- Why this role: {cd['why_this_role']}
- Skills: {skills}
- Projects: {projects}

Rules:
- 3 sentences maximum
- No buzzwords: passionate, driven, results-oriented, dynamic, leverage, excel
- No first-person pronouns (no I, my, me)
- Mention target role and 2-3 specific skills
- Sound like a human, not a job posting

Return ONLY the final objective text. No labels, no commentary."""

    return _call_ai(prompt, max_tokens=200)


def enhance_professional_summary(data: dict) -> str:
    """Generate an ATS-optimized summary for a professional resume."""
    pi = data["personal_info"]
    cp = data["career_positioning"]
    skills = ", ".join(cp["key_expertise"])
    highlights = "; ".join(data.get("key_highlights", [])[:3])
    experience = "; ".join(f"{e['role']} at {e['company']}" for e in data["experience"])

    prompt = f"""You are an expert resume writer specializing in senior professional resumes.

Write a sharp, ATS-optimized professional summary for {pi['name']}.

Context:
- Current Role: {cp['current_role']}
- Total Experience: {cp['total_experience']}
- Target Role: {cp['target_role']}
- Target Industry: {cp['target_industry']}
- Key Expertise: {skills}
- Career Highlights: {highlights}
- Experience: {experience}

Rules:
- 3 sentences maximum
- Use specific facts, numbers, or technologies - not vague claims
- No buzzwords: results-driven, passionate, detail-oriented, dynamic, innovative, leverage, excel, poised, seasoned
- No first-person pronouns (no I, my, me)
- Mention years of experience, target role, and top 2-3 expertise areas
- Sound like a human, not a job posting

Return ONLY the final summary text. No labels, no commentary."""

    return _call_ai(prompt, max_tokens=250)
