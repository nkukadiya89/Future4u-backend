from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from city.models import City
from country.models import Country
from state.models import State
from internship_job.models import Job
from user_profile.models import CorporateProfile
from job_generation.constants.job_generation_constants import (
    JOB_OVERVIEW_MAX_LENGTH,
    JOB_OVERVIEW_MIN_LENGTH,
    JOB_TITLE_MAX_LENGTH,
)


class JobGenerationInputSerializer(serializers.Serializer):
    job_title = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=JOB_TITLE_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Optional. Desired job title hint for AI generation (e.g. 'Senior Data Analyst').",
    )
    job_overview = serializers.CharField(
        min_length=JOB_OVERVIEW_MIN_LENGTH,
        max_length=JOB_OVERVIEW_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Brief role overview used as primary context for AI generation.",
    )
    corporate = serializers.PrimaryKeyRelatedField(
        queryset=CorporateProfile.objects.filter(deleted=False),
        help_text="CorporateProfile ID of the company posting this job.",
    )
    country = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        queryset=Country.objects.filter(deleted=False),
        help_text="Optional. Job location country.",
    )
    state = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        queryset=State.objects.filter(deleted=False),
        help_text="Optional. Job location state.",
    )
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.filter(deleted=False),
        required=False,
        allow_null=True,
        help_text="Job location city (user-provided).",
    )
    salary_min = serializers.DecimalField(
        required=False,
        allow_null=True,
        default=None,
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        help_text="Minimum salary in INR (e.g. 400000).",
    )
    salary_max = serializers.DecimalField(
        required=False,
        allow_null=True,
        default=None,
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        help_text="Maximum salary in INR (e.g. 600000).",
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

        salary_min = attrs.get("salary_min")
        salary_max = attrs.get("salary_max")
        if salary_min is not None and salary_max is not None:
            if salary_min > salary_max:
                raise serializers.ValidationError(
                    {
                        "salary_min": "salary_min must be less than or equal to salary_max."
                    }
                )

        return attrs
