"""
AI service — resume summary enhancement.

Provider priority:
1. OpenAI  (if OPENAI_API_KEY is set)
2. Groq    (if GROQ_API_KEY is set, used as fallback)

If OpenAI fails (quota, auth, network), automatically retries with Groq.
Raises ValueError only if both providers are unavailable.
"""
from __future__ import annotations

import logging

from resume_builder.resume_services.config import (
    OPENAI_API_KEY, OPENAI_MODEL,
    GROQ_API_KEY,   GROQ_MODEL,
)

logger = logging.getLogger(__name__)


# ── OpenAI ────────────────────────────────────────────────────────────────────

def _call_openai(prompt: str, max_tokens: int) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ── Groq ──────────────────────────────────────────────────────────────────────

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


# ── Dispatcher — tries OpenAI first, falls back to Groq ──────────────────────

def _call_ai(prompt: str, max_tokens: int) -> str:
    """
    Try OpenAI first. If it fails (quota, auth, network error),
    fall back to Groq. Raises ValueError if both are unavailable.
    """
    if OPENAI_API_KEY:
        try:
            result = _call_openai(prompt, max_tokens)
            logger.info("AI summary generated via OpenAI")
            return result
        except Exception as exc:
            logger.warning("OpenAI failed (%s), falling back to Groq", exc)

    if GROQ_API_KEY:
        try:
            result = _call_groq(prompt, max_tokens)
            logger.info("AI summary generated via Groq (fallback)")
            return result
        except Exception as exc:
            logger.error("Groq also failed: %s", exc)
            raise ValueError(f"Both AI providers failed. Last error: {exc}")

    raise ValueError(
        "No AI provider configured. Set OPENAI_API_KEY or GROQ_API_KEY in .env"
    )


# ── Public functions ──────────────────────────────────────────────────────────

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
    experience = "; ".join(
        f"{e['role']} at {e['company']}" for e in data["experience"]
    )

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
- Use specific facts, numbers, or technologies — not vague claims
- No buzzwords: results-driven, passionate, detail-oriented, dynamic, innovative, leverage, excel, poised, seasoned
- No first-person pronouns (no I, my, me)
- Mention years of experience, target role, and top 2-3 expertise areas
- Sound like a human, not a job posting

Return ONLY the final summary text. No labels, no commentary."""

    return _call_ai(prompt, max_tokens=250)
