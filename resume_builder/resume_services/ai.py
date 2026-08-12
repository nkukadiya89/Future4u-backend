"""AI service for resume content enhancement.

The LLM now writes ALL resume content — summary, experience bullets,
projects, skills, certifications, highlights — as a structured JSON object.
Every prompt follows the same writing rules: MEDIUM-LEVEL English, plain
human language, no buzzwords, no invented facts.
"""

from __future__ import annotations

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from ai.provider import get_chat_model
from utils.token_usage import extract_token_usage

logger = logging.getLogger(__name__)

_MAX_GENERATION_ATTEMPTS = 2

# Per-resume-type output token budget (the whole content, not just a summary).
_FRESHER_MAX_TOKENS = 2200
_PROFESSIONAL_MAX_TOKENS = 2600

# Shared writing style rules — applied to every resume prompt.
WRITING_RULES = """\
WRITING STYLE RULES (very important):
- Write in MEDIUM-LEVEL ENGLISH: simple, clear, everyday words that any hiring manager can understand in one read.
- Sound like a real human wrote it, not like a job posting or an AI bot.
- Use short, natural sentences. Never use long, complicated, or fancy sentences.
- No buzzwords, jargon, or filler phrases (e.g. passionate, driven, results-oriented, dynamic, leverage, utilize, synergy, world-class, detail-oriented, team player, seamless, robust).
- No first-person pronouns (no I, my, me, we, our).
- NEVER invent facts: no fake numbers, companies, dates, degrees, or achievements. Only reword and polish what is given.
- Keep bullet points short (8-12 words each) and easy to read.
- Never return markdown, code fences, labels, or commentary. Return ONLY valid JSON."""


def _build_fresher_prompt(data: dict) -> str:
    """Build the prompt that rewrites a fresher/student resume in full."""
    return f"""\
You are an expert resume writer for students and freshers.

Rewrite the resume below so that EVERY section is polished, ATS-friendly, and
written in medium-level, human-friendly English. Keep all facts exactly as
provided — same companies, dates, degrees, skill names — but reword every
sentence into natural, confident language a hiring manager will enjoy reading.

{WRITING_RULES}

Here is the raw profile data:
{json.dumps(data, ensure_ascii=False, indent=2)}

Return a JSON object with EXACTLY this structure (use the same keys):

{{
  "summary": "3-sentence career objective. Mention the target role and 2-3 specific skills.",
  "career_direction": {{
    "target_role": "as provided",
    "target_industry": "as provided",
    "why_this_role": "1-2 natural sentences, reworded"
  }},
  "education": [
    {{"institution": "as provided", "degree": "as provided", "field": "as provided", "year": 2024, "cgpa": 8.5}}
  ],
  "skills": {{
    "technical": ["3-8 clean skill names"],
    "soft": ["3-5 human-friendly soft skills, no buzzwords"]
  }},
  "projects": [
    {{
      "title": "as provided",
      "problem_statement": "1 sentence, simple English",
      "your_role": "1 sentence",
      "technologies": ["as provided"],
      "impact": "1 sentence, only if provided"
    }}
  ],
  "internships": [
    {{
      "company": "as provided",
      "duration": "as provided",
      "responsibilities": ["2-4 short bullets"],
      "key_achievement": "1 short line, only if provided"
    }}
  ],
  "certifications": [
    {{"name": "as provided", "issuer": "as provided", "year": 2023}}
  ],
  "achievements": ["short, natural lines"],
  "extra_activities": ["short, natural lines"],
  "additional_insights": ["short, natural lines"],
  "strengths": ["3-5 genuine strengths in plain words"],
  "preferred_locations": ["only if provided"]
}}

Rules for the content:
- The summary must be 3 sentences maximum, mention the target role, and be written in warm, plain English.
- Rewrite every project, internship, and achievement bullet so it reads naturally. Do not copy the raw text word-for-word.
- If a field is empty in the input, return an empty value for it.
"""


def _build_professional_prompt(data: dict) -> str:
    """Build the prompt that rewrites a professional resume in full."""
    return f"""\
You are an expert resume writer for working professionals.

Rewrite the resume below so that EVERY section is polished, ATS-friendly, and
written in medium-level, human-friendly English. Keep all facts exactly as
provided — same companies, roles, dates, degree names — but reword every
sentence into natural, confident language a hiring manager will enjoy reading.

{WRITING_RULES}

Here is the raw profile data:
{json.dumps(data, ensure_ascii=False, indent=2)}

Return a JSON object with EXACTLY this structure (use the same keys):

{{
  "summary": "3-sentence professional summary. Mention years of experience, current or target role, and 2-3 areas of expertise.",
  "career_positioning": {{
    "current_role": "as provided",
    "total_experience": "as provided",
    "target_role": "as provided",
    "target_industry": "as provided",
    "key_expertise": ["3-5 areas, plain words"]
  }},
  "experience": [
    {{
      "company": "as provided",
      "role": "as provided",
      "duration": "as provided",
      "responsibilities": ["2-4 short bullets"],
      "achievements": ["1-2 short bullets, only if provided"],
      "projects": [
        {{"name": "as provided", "role": "as provided", "outcome": "as provided", "technologies": ["as provided"]}}
      ]
    }}
  ],
  "skills": {{
    "technical": ["3-8 clean skill names"],
    "tools": ["as provided"],
    "domain_knowledge": ["as provided"],
    "leadership": ["as provided"]
  }},
  "education": [
    {{"institution": "as provided", "degree": "as provided", "field": "as provided", "year": 2020, "cgpa": 8.5}}
  ],
  "certifications": [
    {{"name": "as provided", "issuer": "as provided", "year": 2023}}
  ],
  "key_highlights": ["2-4 short, factual highlights"],
  "additional_insights": ["short, natural lines"]
}}

Rules for the content:
- The summary must be 3 sentences maximum and use specific facts only (do not invent numbers).
- Rewrite every experience bullet so it reads naturally and shows impact in plain words. Do not copy the raw text word-for-word.
- If a field is empty in the input, return an empty value for it.
"""


def _extract_text_content(result) -> str:
    """Pull plain text out of a LangChain response (string or content blocks)."""
    if isinstance(result, str):
        return result
    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif hasattr(block, "text"):
                parts.append(str(block.text))
        return "".join(parts)
    return str(result)


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` fences the model sometimes wraps output in."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _call_llm_json(prompt: str, max_tokens: int) -> tuple[dict, int]:
    """Invoke the LLM and return (parsed JSON dict, token usage).

    Retries once if the model returns invalid JSON. Raises ValueError on
    provider failure so callers surface a friendly 500.
    """
    chat_template = ChatPromptTemplate.from_messages([("user", "{input}")])
    chain = chat_template | get_chat_model(max_tokens=max_tokens, temperature=0.7)

    last_error: Exception | None = None
    for attempt in range(_MAX_GENERATION_ATTEMPTS):
        try:
            response = chain.invoke({"input": prompt})
            token_usage = extract_token_usage(response)
            raw_text = _extract_text_content(response)
            if not raw_text or not raw_text.strip():
                raise ValueError("AI returned an empty response")
            parsed = json.loads(_strip_code_fences(raw_text))
            if not isinstance(parsed, dict):
                raise ValueError("AI response root must be a JSON object")
            return parsed, token_usage
        except json.JSONDecodeError as exc:
            last_error = exc
            logger.warning(
                "Resume AI JSON parse failed (attempt %s/%s): %s",
                attempt + 1,
                _MAX_GENERATION_ATTEMPTS,
                exc,
            )
        except ValueError as exc:
            last_error = exc
            logger.warning(
                "Resume AI response invalid (attempt %s/%s): %s",
                attempt + 1,
                _MAX_GENERATION_ATTEMPTS,
                exc,
            )

    logger.error("Resume AI failed after retries: %s", last_error)
    raise ValueError(f"AI provider failed. Last error: {last_error}") from last_error


def enhance_resume_content(data: dict) -> tuple[dict, int]:
    """Enhance ALL resume content via the LLM.

    Returns (llm_generated_content_dict, token_usage). The caller merges the
    result over the profile data; factual fields are protected there.
    """
    resume_type = data.get("resume_type")
    if resume_type == "fresher":
        prompt = _build_fresher_prompt(data)
        max_tokens = _FRESHER_MAX_TOKENS
    else:
        prompt = _build_professional_prompt(data)
        max_tokens = _PROFESSIONAL_MAX_TOKENS

    logger.info("Generating full AI resume content (type=%s)", resume_type)
    result, token_usage = _call_llm_json(prompt, max_tokens)
    logger.info(
        "AI resume content generated (type=%s, token_usage=%s)", resume_type, token_usage
    )
    return result, token_usage
