from __future__ import annotations

from typing import Any

from course_generation.exceptions import CourseGenerationAccessDeniedError
from course_generation.schemas.course_output import CourseGenerationPayload
from course_generation.selectors.course_generation_access import can_user_generate_courses
from course_generation.services.course_generator import CourseGenerator


class CourseGenerationService:
    """Orchestrates AI course detail generation for institute users."""

    def generate(self, *, user, validated_input: dict[str, Any]) -> dict[str, Any]:
        if not can_user_generate_courses(user):
            raise CourseGenerationAccessDeniedError(
                "Course generation is only available for institute accounts"
            )

        payload = CourseGenerator.generate(generation_input=validated_input)
        return _build_response(payload, validated_input)


def _build_response(
    payload: CourseGenerationPayload, validated_input: dict[str, Any]
) -> dict[str, Any]:
    data = payload.model_dump()
    for field in ("course_price", "course_type", "mode", "duration"):
        if field in validated_input:
            data[field] = validated_input[field]
    return data
