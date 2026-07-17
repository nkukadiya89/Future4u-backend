from __future__ import annotations

from rest_framework import serializers

from city.models import City
from country.models import Country
from state.models import State
from internship_job.models import Internship
from internship_generation.constants.internship_generation_constants import (
    INTERNSHIP_OVERVIEW_INPUT_MAX_LENGTH,
    INTERNSHIP_OVERVIEW_INPUT_MIN_LENGTH,
    OPTIONAL_FIELD_MAX_LENGTH,
)
from user.models import User


class InternshipGenerationInputSerializer(serializers.Serializer):
    internship_title = serializers.CharField(
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        trim_whitespace=True,
        help_text="Internship title provided by the employer.",
    )
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
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        required=False,
        allow_null=True,
        help_text="Country ID where the internship is located.",
    )
    state = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(),
        required=False,
        allow_null=True,
        help_text="State ID where the internship is located.",
    )
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        required=False,
        allow_null=True,
        help_text="City ID where the internship is located.",
    )
    certificate_provided = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Whether a completion certificate is provided.",
    )
    # Dropdown 1 — type of organisation posting this internship
    provider_type = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=Internship.PROVIDER_TYPE_CHOICES,
        help_text="Select whether this internship is posted by an Institute or a Corporate.",
    )
    # Dropdown 2 — specific user of the selected provider_type
    internship_provider = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        queryset=User.objects.filter(
            user_type__in=["institute", "corporate"],
            deleted=False,
        ),
        help_text="Select the institute or corporate posting this internship.",
    )

    def validate(self, attrs):
        for field_name in ("department", "stipend", "duration", "mode", "provider_type"):
            if attrs.get(field_name) == "":
                attrs.pop(field_name, None)

        provider_type = attrs.get("provider_type")
        internship_provider = attrs.get("internship_provider")
        if internship_provider and provider_type:
            if internship_provider.user_type != provider_type:
                raise serializers.ValidationError(
                    {
                        "internship_provider": (
                            f"Selected user does not belong to the '{provider_type}' type."
                        )
                    }
                )
        return attrs
