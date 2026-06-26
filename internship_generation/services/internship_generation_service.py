from __future__ import annotations

from typing import Any

from internship_generation.exceptions import InternshipGenerationAccessDeniedError
from internship_generation.schemas.internship_output import InternshipGenerationPayload
from internship_generation.selectors.internship_generation_access import (
    can_user_generate_internships,
)
from internship_generation.services.internship_generator import InternshipGenerator


class InternshipGenerationService:
    """Orchestrates AI internship detail generation for corporate/employer users."""

    def generate(self, *, user, validated_input: dict[str, Any]) -> dict[str, Any]:
        if not can_user_generate_internships(user):
            raise InternshipGenerationAccessDeniedError(
                "Internship generation is only available for corporate and employer accounts"
            )

        payload = InternshipGenerator.generate(generation_input=validated_input)
        return _build_response(payload, validated_input)


def _build_response(
    payload: InternshipGenerationPayload, validated_input: dict[str, Any]
) -> dict[str, Any]:
    data = payload.model_dump()
    for field in ("department", "stipend", "duration", "mode", "application_deadline"):
        if field not in validated_input:
            continue
        value = validated_input[field]
        if field == "application_deadline" and value is not None:
            data[field] = value.isoformat()
        else:
            data[field] = value
    return data
