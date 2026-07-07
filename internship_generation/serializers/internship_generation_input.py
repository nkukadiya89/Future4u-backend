from __future__ import annotations

from rest_framework import serializers

from internship_job.models import Internship
from internship_generation.constants.internship_generation_constants import (
    INTERNSHIP_OVERVIEW_INPUT_MAX_LENGTH,
    INTERNSHIP_OVERVIEW_INPUT_MIN_LENGTH,
    OPTIONAL_FIELD_MAX_LENGTH,
)


class InternshipGenerationInputSerializer(serializers.Serializer):
    internship_overview = serializers.CharField(
        min_length=INTERNSHIP_OVERVIEW_INPUT_MIN_LENGTH,
        max_length=INTERNSHIP_OVERVIEW_INPUT_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Brief internship overview used as primary context for AI generation.",
    )
    department = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Department (user-provided).",
    )
    stipend = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Monthly stipend amount (user-provided).",
    )
    duration = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Internship duration (e.g. 3 Months).",
    )
    mode = serializers.ChoiceField(
        choices=Internship.MODE_CHOICE,
        required=False,
        allow_blank=True,
        help_text="Work mode (same values as Internship model).",
    )
    application_deadline = serializers.DateField(
        required=False,
        allow_null=True,
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"],
        help_text="Application deadline (DD/MM/YYYY or YYYY-MM-DD), or omit when there is no deadline.",
    )

    def validate(self, attrs):
        for field_name in ("department", "stipend", "duration", "mode"):
            if attrs.get(field_name) == "":
                attrs.pop(field_name, None)
        return attrs
