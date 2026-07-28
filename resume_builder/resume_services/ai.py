"""AI service for resume summary enhancement."""

from __future__ import annotations

import logging

from langchain_core.prompts import ChatPromptTemplate

from ai.provider import get_chat_model
from utils.token_usage import extract_token_usage

logger = logging.getLogger(__name__)


def _call_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
    chat_template = ChatPromptTemplate.from_messages(
        [
            ("user", "{input}"),
        ]
    )
    chain = chat_template | get_chat_model(max_tokens=max_tokens, temperature=0.7)
    response = chain.invoke({"input": prompt})
    token_usage = extract_token_usage(response)
    return response.content.strip(), token_usage


def _call_ai(prompt: str, max_tokens: int) -> tuple[str, int]:
    try:
        result, token_usage = _call_llm(prompt, max_tokens)
        logger.info("AI summary generated")
        return result, token_usage
    except Exception as exc:
        logger.error("AI provider failed: %s", exc)
        raise ValueError(f"AI provider failed. Last error: {exc}") from exc


def enhance_fresher_summary(data: dict) -> tuple[str, int]:
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


def enhance_professional_summary(data: dict) -> tuple[str, int]:
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
