from __future__ import annotations

from typing import Any

from course_generation.exceptions import CourseGenerationAccessDeniedError
from course_generation.schemas.course_output import CourseGenerationPayload
from course_generation.selectors.course_generation_access import (
    can_user_generate_courses,
)
from course_generation.services.course_generator import CourseGenerator


class CourseGenerationService:
    """Orchestrates AI course detail generation for institute users."""

    def generate(
        self, *, user, validated_input: dict[str, Any], feature_code=None
    ) -> tuple[dict[str, Any], int]:
        if not can_user_generate_courses(user):
            raise CourseGenerationAccessDeniedError(
                "Course generation is only available for institute and school/college accounts"
            )

        payload, token_usage = CourseGenerator.generate(
            generation_input=validated_input,
            user=user,
            feature_code=feature_code,
        )
        return _build_response(payload, validated_input), token_usage


def _build_response(
    payload: CourseGenerationPayload, validated_input: dict[str, Any]
) -> dict[str, Any]:
    data = payload.model_dump()

    # course_title — AI-generated (pre-fills the title field on the form)
    # already in data from payload.model_dump()

    # Map AI-generated course_overview → course_description
    if "course_overview" in data:
        data["course_description"] = data.pop("course_overview")

    # Preserve the user's original course_overview input
    if "course_overview" in validated_input:
        data["course_overview"] = validated_input["course_overview"]

    # Pass through user-provided fields
    for field in ("course_price", "course_type", "mode", "duration"):
        if field in validated_input:
            data[field] = validated_input[field]

    country = validated_input.get("country")
    data["country"] = country.pk if country else None
    data["country_name"] = country.name if country else ""
    state = validated_input.get("state")
    data["state"] = state.pk if state else None
    data["state_name"] = state.name if state else ""
    city = validated_input.get("city")
    data["city"] = city.pk if city else None
    data["city_name"] = city.name if city else ""

    # Pass through provider_type and course_provider (same pattern as country/state/city)
    data["provider_type"] = validated_input.get("provider_type") or None

    course_provider = validated_input.get("course_provider")
    data["course_provider"] = course_provider.pk if course_provider else None
    # Resolve display name from profile
    course_provider_name = None
    if course_provider:
        if hasattr(course_provider, "institute_profile"):
            course_provider_name = getattr(
                course_provider.institute_profile, "institute_name", None
            )
        if not course_provider_name and hasattr(
            course_provider, "school_college_profile"
        ):
            course_provider_name = getattr(
                course_provider.school_college_profile, "institute_name", None
            )
        if not course_provider_name:
            course_provider_name = getattr(course_provider, "full_name", None) or ""
    data["course_provider_name"] = course_provider_name or ""

    return data
