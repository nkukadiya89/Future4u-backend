from __future__ import annotations

from rest_framework import serializers

from course.models import Courses
from course_generation.constants.course_generation_constants import (
    COURSE_OVERVIEW_MAX_LENGTH,
    COURSE_OVERVIEW_MIN_LENGTH,
    OPTIONAL_FIELD_MAX_LENGTH,
)


class CourseGenerationInputSerializer(serializers.Serializer):
    course_overview = serializers.CharField(
        min_length=COURSE_OVERVIEW_MIN_LENGTH,
        max_length=COURSE_OVERVIEW_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Brief course overview used as primary context for AI generation.",
    )
    course_price = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Course price (user-provided).",
    )
    course_type = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=Courses.COURSE_TYPE_CHOICES,
        help_text="Course type (same values as Courses model).",
    )
    mode = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=Courses.MODE_CHOICE,
        help_text="Delivery mode (same values as Courses model).",
    )
    duration = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Course duration (e.g. 8 Weeks).",
    )

    def validate(self, attrs):
        for field_name in ("course_type", "mode"):
            if attrs.get(field_name) == "":
                attrs.pop(field_name, None)
        return attrs
