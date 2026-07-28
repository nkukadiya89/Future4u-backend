"""
Serializers for the LinkedIn Job Search integration.

Contains:
- JobSearchQuerySerializer  – validates / normalises incoming query params
- JobNormalizedSerializer   – validates and represents normalised job data

The raw API response is mapped into the normalised format inside the service
layer *before* being passed to JobNormalizedSerializer, which keeps the
serializer simple and avoids DRF ``source`` parameter pitfalls.
"""

from rest_framework import serializers


class JobSearchQuerySerializer(serializers.Serializer):
    """Validates and sanitises the incoming job search query parameters."""

    title = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
        trim_whitespace=True,
        help_text="Job title keyword(s).",
    )
    location = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
        trim_whitespace=True,
        help_text="Location (city, state, or country string).",
    )
    country = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        trim_whitespace=True,
    )
    state = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        trim_whitespace=True,
    )
    city = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        trim_whitespace=True,
    )
    experience_level = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        trim_whitespace=True,
    )
    employment_type = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        trim_whitespace=True,
    )
    remote = serializers.BooleanField(required=False, default=None, allow_null=True)
    hybrid = serializers.BooleanField(required=False, default=None, allow_null=True)
    salary_min = serializers.IntegerField(required=False, min_value=0)
    salary_max = serializers.IntegerField(required=False, min_value=0)
    company = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
        trim_whitespace=True,
    )
    posted_within = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=20,
        trim_whitespace=True,
    )
    limit = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1,
        max_value=50,
    )
    page = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
    )

    def validate(self, attrs):
        """Ensure salary_min <= salary_max when both are provided."""
        salary_min = attrs.get("salary_min")
        salary_max = attrs.get("salary_max")
        if (
            salary_min is not None
            and salary_max is not None
            and salary_min > salary_max
        ):
            raise serializers.ValidationError(
                {
                    "salary_max": "salary_max must be greater than or equal to salary_min."
                }
            )
        return attrs


class JobNormalizedSerializer(serializers.Serializer):
    """
    Validates and represents a normalised job object.

    This serializer expects data that has already been mapped into the
    standard Future4u format by the service layer.

    Every field has a safe default so missing data never breaks the response.
    null arrays are replaced with empty lists in ``to_representation``.
    """

    id = serializers.CharField(default="", allow_blank=True)
    title = serializers.CharField(default="", allow_blank=True)
    company = serializers.CharField(default="", allow_blank=True)
    company_logo = serializers.CharField(default="", allow_blank=True)
    location = serializers.CharField(default="", allow_blank=True)
    country = serializers.CharField(default="", allow_blank=True)
    city = serializers.CharField(default="", allow_blank=True)
    state = serializers.CharField(default="", allow_blank=True)
    employment_type = serializers.CharField(default="", allow_blank=True)
    experience_level = serializers.CharField(default="", allow_blank=True)
    salary_min = serializers.FloatField(default=None, allow_null=True)
    salary_max = serializers.FloatField(default=None, allow_null=True)
    currency = serializers.CharField(default="INR", allow_blank=True)
    remote_type = serializers.CharField(default="", allow_blank=True)
    description = serializers.CharField(default="", allow_blank=True)
    skills = serializers.ListField(
        child=serializers.CharField(), default=list, allow_null=True
    )
    posted_at = serializers.CharField(default="", allow_blank=True)
    apply_url = serializers.CharField(default="", allow_blank=True)
    source = serializers.CharField(default="linkedin", allow_blank=True)
    company_size = serializers.CharField(default="", allow_blank=True)
    industry = serializers.CharField(default="", allow_blank=True)
    seniority = serializers.CharField(default="", allow_blank=True)
    job_url = serializers.CharField(default="", allow_blank=True)

    def to_representation(self, instance):
        """Ensure null arrays become empty lists."""
        data = super().to_representation(instance)
        for field in ("skills",):
            if data.get(field) is None:
                data[field] = []
        return data
