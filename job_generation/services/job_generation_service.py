from __future__ import annotations

from typing import Any

from job_generation.exceptions import JobGenerationAccessDeniedError
from job_generation.schemas.job_output import JobGenerationPayload
from job_generation.selectors.job_generation_access import can_user_generate_jobs
from job_generation.services.job_generator import JobGenerator


class JobGenerationService:
    """Orchestrates AI job posting generation for institute and corporate users."""

    def generate(self, *, user, validated_input: dict[str, Any]) -> dict[str, Any]:
        if not can_user_generate_jobs(user):
            raise JobGenerationAccessDeniedError(
                "Job generation is only available for institute and corporate accounts"
            )

        payload = JobGenerator.generate(generation_input=validated_input)
        return _build_response(payload, validated_input)


def _build_response(
    payload: JobGenerationPayload, validated_input: dict[str, Any]
) -> dict[str, Any]:
    data = payload.model_dump()
    data["organization_name"] = validated_input.get("organization_name", "")
    city = validated_input.get("city")
    data["city"] = city.pk if city else None
    data["city_name"] = city.name if city else ""
    data["salary_range"] = validated_input.get("salary_range", "")
    data["job_type"] = validated_input.get("job_type", "")
    data["experience_level"] = validated_input.get("experience_level", "")
    data["mode"] = validated_input.get("mode", "")
    deadline = validated_input.get("application_deadline")
    data["application_deadline"] = deadline.isoformat() if deadline else None
    return data


# Kept for admin panel compatibility during testing.
def _apply_user_overrides(
    payload: JobGenerationPayload, validated_input: dict[str, Any]
) -> dict[str, Any]:
    return _build_response(payload, validated_input)
