from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from internship_generation.schemas.internship_output import InternshipGenerationPayload


def parse_ai_payload(payload: Any) -> InternshipGenerationPayload:
    if isinstance(payload, InternshipGenerationPayload):
        return payload
    if isinstance(payload, dict):
        return InternshipGenerationPayload.model_validate(_normalize_payload(payload))
    raise ValueError("AI response must be a JSON object")


def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "title": "internship_title",
        "internshipTitle": "internship_title",
        "name": "internship_title",
        "about": "about_internship",
        "aboutInternship": "about_internship",
        "description": "about_internship",
        "responsibilities": "key_responsibilities",
        "keyResponsibilities": "key_responsibilities",
        "requiredSkills": "skills",
        "required_skills": "skills",
    }

    normalized: dict[str, Any] = {}
    for key, value in data.items():
        target = aliases.get(key, key)
        if target in normalized and normalized[target] not in (None, "", []):
            continue
        normalized[target] = value

    return normalized
