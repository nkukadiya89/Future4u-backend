from __future__ import annotations

from rest_framework import serializers

from city.models import City
from internship_job.models import Job
from job_generation.constants.job_generation_constants import (
    JOB_SUMMARY_MAX_LENGTH,
    JOB_SUMMARY_MIN_LENGTH,
    OPTIONAL_FIELD_MAX_LENGTH,
)


class JobGenerationInputSerializer(serializers.Serializer):
    job_summary = serializers.CharField(
        min_length=JOB_SUMMARY_MIN_LENGTH,
        max_length=JOB_SUMMARY_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Brief role summary used as primary context for AI generation.",
    )
    organization_name = serializers.CharField(
        min_length=2,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Company or organization name (user-provided).",
    )
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.filter(deleted=False),
        required=False,
        allow_null=True,
        help_text="Job location city (user-provided).",
    )
    salary_range = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Salary range (e.g. ₹6 - 10 LPA).",
    )
    job_type = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=Job.JOB_TYPE_CHOICE,
        help_text="Job type (same values as Job model).",
    )
    experience_level = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=Job.EXPERIENCE_CHOICES,
        help_text="Experience level (same values as Job model).",
    )
    mode = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=Job.MODE_CHOICES,
        help_text="Work mode (same values as Job model).",
    )
    application_deadline = serializers.DateField(
        required=False,
        allow_null=True,
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"],
        help_text="Application deadline (DD/MM/YYYY or YYYY-MM-DD), or omit when there is no deadline.",
    )

    def validate(self, attrs):
        for field_name in ("job_type", "experience_level", "mode"):
            if attrs.get(field_name) == "":
                attrs.pop(field_name, None)
        return attrs
