from rest_framework import serializers

from common.serializers import BaseModelSerializer
from user.models import User

from .models import Internship, InternshipApplication, Job, JobApplication


class InternshipSerializer(BaseModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    provider_name = serializers.SerializerMethodField()
    internship_provider_name = serializers.SerializerMethodField()

    # Field aliases for the AI generation pipeline / frontend payload
    internship_overview = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Employer-provided internship overview used as AI generation context.",
    )
    internship_title = serializers.CharField(
        source="name",
        max_length=250,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Alias for 'name' — maps internship_title → name.",
    )
    about_internship = serializers.CharField(
        source="description",
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Alias for 'description' — maps about_internship → description.",
    )
    key_responsibilities = serializers.ListField(
        source="responsibilities",
        required=False,
        allow_null=True,
        child=serializers.CharField(),
        help_text="Alias for 'responsibilities' — maps key_responsibilities → responsibilities.",
    )
    stipend = serializers.DecimalField(
        source="stipend_amount",
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Alias for 'stipend_amount' — maps stipend → stipend_amount.",
    )

    # Dropdown 1 — type of organisation posting this internship
    provider_type = serializers.ChoiceField(
        choices=Internship.PROVIDER_TYPE_CHOICES,
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    # Dropdown 2 — internship provider (institute/corporate user)
    internship_provider = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(
            user_type__in=["institute", "corporate"],
            deleted=False,
        ),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Internship
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "name",
            "internship_title",
            "internship_overview",
            "department",
            "country",
            "country_name",
            "state",
            "state_name",
            "city",
            "city_name",
            "description",
            "about_internship",
            "responsibilities",
            "key_responsibilities",
            "skills",
            "education_tags",
            "internship_type",
            "mode",
            "duration",
            "fees_amount",
            "stipend_amount",
            "stipend",
            "certificate_provided",
            "provider",
            "provider_name",
            "provider_type",
            "internship_provider",
            "internship_provider_name",
            "application_deadline",
            "status",
        ]

    def get_provider_name(self, obj):
        if obj.provider:
            return obj.provider.full_name
        return None

    def get_internship_provider_name(self, obj):
        if obj.internship_provider:
            if hasattr(obj.internship_provider, "institute_profile"):
                name = obj.internship_provider.institute_profile.institute_name
                if name:
                    return name
            if hasattr(obj.internship_provider, "corporate_profile"):
                name = obj.internship_provider.corporate_profile.company_name
                if name:
                    return name
            return obj.internship_provider.full_name
        return None


class InternshipApplicationSerializer(BaseModelSerializer):
    applicant_name = serializers.CharField(source="applicant.full_name", read_only=True)
    applicant_type = serializers.CharField(source="applicant.user_type", read_only=True)
    internship_name = serializers.CharField(source="internship.name", read_only=True)

    class Meta:
        model = InternshipApplication
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "applicant",
            "applicant_name",
            "applicant_type",
            "internship",
            "internship_name",
            "resume",
            "status",
            "applied_at",
        ]
        read_only_fields = [
            "applicant",
            "applied_at",
        ]


class JobSerializer(BaseModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    provider_name = serializers.SerializerMethodField()
    education_tags_name = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "name",
            "corporate",
            "job_overview",
            "description",
            "responsibilities",
            "skills",
            "education_tags",
            "education_tags_name",
            "experience_level",
            "job_type",
            "mode",
            "country",
            "country_name",
            "state",
            "state_name",
            "city",
            "city_name",
            "salary_min",
            "salary_max",
            "provider",
            "provider_name",
            "why_this_match",
            "status",
            "application_deadline",
        ]

    def get_provider_name(self, obj):
        if obj.provider:
            return obj.provider.full_name
        return None

    def get_education_tags_name(self, obj):
        return list(obj.education_tags.values_list("level_code", flat=True))


class JobApplicationSerializer(BaseModelSerializer):
    applicant_name = serializers.CharField(source="applicant.full_name", read_only=True)
    applicant_type = serializers.CharField(source="applicant.user_type", read_only=True)
    job_name = serializers.CharField(source="job.name", read_only=True)

    class Meta:
        model = JobApplication
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "applicant",
            "applicant_name",
            "applicant_type",
            "job",
            "job_name",
            "resume",
            "status",
            "applied_at",
        ]
        read_only_fields = [
            "applicant",
            "applied_at",
        ]
