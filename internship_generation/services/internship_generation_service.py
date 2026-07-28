from __future__ import annotations

from typing import Any

from internship_generation.exceptions import InternshipGenerationAccessDeniedError
from internship_generation.schemas.internship_output import InternshipGenerationPayload
from internship_generation.selectors.internship_generation_access import (
    can_user_generate_internships,
)
from internship_generation.services.internship_generator import InternshipGenerator


class InternshipGenerationService:
    """Orchestrates AI internship detail generation for institute and corporate users."""

    def generate(
        self, *, user, validated_input: dict[str, Any]
    ) -> tuple[dict[str, Any], int]:
        if not can_user_generate_internships(user):
            raise InternshipGenerationAccessDeniedError(
                "Internship generation is only available for institute and corporate accounts"
            )

        payload, token_usage = InternshipGenerator.generate(
            generation_input=validated_input
        )
        return _build_response(payload, validated_input), token_usage


def _build_response(
    payload: InternshipGenerationPayload, validated_input: dict[str, Any]
) -> dict[str, Any]:
    data = payload.model_dump()
    for field in (
        "internship_overview",
        "department",
        "stipend",
        "duration",
        "mode",
        "application_deadline",
        "country",
        "state",
        "city",
        "certificate_provided",
    ):
        if field not in validated_input:
            continue
        value = validated_input[field]
        if value is None:
            continue
        if field == "application_deadline" and value is not None:
            data[field] = value.isoformat()
        elif field in ("country", "state", "city"):
            data[field] = value.pk if hasattr(value, "pk") else value
        else:
            data[field] = value

    data["provider_type"] = validated_input.get("provider_type") or None

    internship_provider = validated_input.get("internship_provider")
    data["internship_provider"] = (
        internship_provider.pk if internship_provider else None
    )

    internship_provider_name = None
    if internship_provider:
        if hasattr(internship_provider, "institute_profile"):
            internship_provider_name = getattr(
                internship_provider.institute_profile, "institute_name", None
            )
        if not internship_provider_name and hasattr(
            internship_provider, "corporate_profile"
        ):
            internship_provider_name = getattr(
                internship_provider.corporate_profile, "company_name", None
            )
        if not internship_provider_name:
            internship_provider_name = (
                getattr(internship_provider, "full_name", None) or ""
            )
    data["internship_provider_name"] = internship_provider_name or ""
    data["status"] = "draft"

    return data
