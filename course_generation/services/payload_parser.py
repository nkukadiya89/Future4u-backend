from __future__ import annotations

from typing import Any

from course_generation.schemas.course_output import CourseGenerationPayload


def parse_ai_payload(payload: Any) -> CourseGenerationPayload:
    if isinstance(payload, CourseGenerationPayload):
        return payload
    if isinstance(payload, dict):
        return CourseGenerationPayload.model_validate(_normalize_payload(payload))
    raise ValueError("AI response must be a JSON object")


def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "title": "course_title",
        "courseTitle": "course_title",
        "name": "course_title",
        "overview": "course_overview",
        "courseOverview": "course_overview",
        "requiredSkills": "skills",
        "required_skills": "skills",
        "modules": "course_content",
        "courseContent": "course_content",
        "course_modules": "course_content",
        "whyThisCourse": "why_this_course",
        "why_this_courses": "why_this_course",
        "certificationInfo": "certification_info",
        "certification": "certification_info",
    }

    normalized: dict[str, Any] = {}
    for key, value in data.items():
        target = aliases.get(key, key)
        if target in normalized and normalized[target] not in (None, "", []):
            continue
        normalized[target] = value

    return normalized
