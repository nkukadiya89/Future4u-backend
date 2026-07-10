from __future__ import annotations

from rest_framework import serializers

from city.models import City
from country.models import Country
from course.models import Courses
from course_generation.constants.course_generation_constants import (
    COURSE_OVERVIEW_MAX_LENGTH,
    COURSE_OVERVIEW_MIN_LENGTH,
    COURSE_TITLE_MAX_LENGTH,
    OPTIONAL_FIELD_MAX_LENGTH,
)
from state.models import State
from user.models import User


class CourseGenerationInputSerializer(serializers.Serializer):
    course_title = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=COURSE_TITLE_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Optional. Course title hint — AI will refine and professionalize it.",
    )
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
    country = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        queryset=Country.objects.filter(deleted=False),
        help_text="Optional. Country where the course is offered.",
    )
    state = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        queryset=State.objects.filter(deleted=False),
        help_text="Optional. State where the course is offered.",
    )
    city = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        queryset=City.objects.filter(deleted=False),
        help_text="Optional. City where the course is offered.",
    )
    # Dropdown 1 — type of organisation posting this course
    provider_type = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=Courses.PROVIDER_TYPE_CHOICES,
        help_text="Select whether this course is posted by a School/College or an Institute.",
    )
    # Dropdown 2 — specific user of the selected provider_type
    course_provider = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        queryset=User.objects.filter(
            user_type__in=["school_college", "institute"],
            deleted=False,
        ),
        help_text="Select the institute or school/college posting this course.",
    )

    def validate(self, attrs):
        for field_name in ("course_type", "mode", "provider_type"):
            if attrs.get(field_name) == "":
                attrs.pop(field_name, None)

        # If course_provider provided, must match the selected provider_type
        provider_type = attrs.get("provider_type")
        course_provider = attrs.get("course_provider")
        if course_provider and provider_type:
            if course_provider.user_type != provider_type:
                raise serializers.ValidationError(
                    {
                        "course_provider": (
                            f"Selected user does not belong to the '{provider_type}' type."
                        )
                    }
                )
        return attrs
