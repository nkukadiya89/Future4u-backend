from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from job_generation.schemas.job_output import JobGenerationPayload


def parse_ai_payload(payload: Any) -> JobGenerationPayload:
    if isinstance(payload, JobGenerationPayload):
        return payload
    if isinstance(payload, dict):
        return JobGenerationPayload.model_validate(_normalize_payload(payload))
    raise ValueError("AI response must be a JSON object")


def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "title": "name",
        "jobTitle": "name",
        "job_title": "name",
        "jobDescription": "description",
        "job_description": "description",
        "keyResponsibilities": "responsibilities",
        "key_responsibilities": "responsibilities",
        "requiredSkills": "skills",
        "required_skills": "skills",
        "whyThisMatches": "why_this_match",
        "why_this_matches": "why_this_match",
        "qualifications": "education_tags",
        "education_level": "education_tags",
        "education_required": "education_tags",
        "education": "education_tags",
    }

    normalized: dict[str, Any] = {}
    for key, value in data.items():
        target = aliases.get(key, key)
        if target in normalized and normalized[target] not in (None, "", []):
            continue
        normalized[target] = value

    return normalized
