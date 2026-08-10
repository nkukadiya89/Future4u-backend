from education_level.serializers import EducationLevelDropdownSerializer
from rest_framework import serializers

from common.serializers import BaseModelSerializer
from user.models import User
from user_profile.serializers import get_role_profile

from .models import (
    Internship,
    InternshipApplication,
    InternshipApplicationNote,
    Job,
    JobApplication,
    JobApplicationNote,
)


class InternshipSerializer(BaseModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    internship_provider_name = serializers.SerializerMethodField()
    education_tags_name = EducationLevelDropdownSerializer(
        source="education_tags", many=True, read_only=True
    )

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
            "education_tags_name",
            "internship_type",
            "mode",
            "duration",
            "fees_amount",
            "stipend_amount",
            "stipend",
            "certificate_provided",
            "created_by",
            "created_by_name",
            "provider_type",
            "internship_provider",
            "internship_provider_name",
            "application_deadline",
            "status",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.full_name
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

    def validate(self, attrs):
        # New internships must carry a name; AI generation provides one via internship_title.
        if self.instance is None and not str(attrs.get("name") or "").strip():
            raise serializers.ValidationError({"name": "This field is required."})
        return attrs


class InternshipApplicationSerializer(BaseModelSerializer):
    applicant_name = serializers.CharField(source="applicant.full_name", read_only=True)
    applicant_type = serializers.CharField(source="applicant.user_type", read_only=True)
    internship_name = serializers.CharField(source="internship.name", read_only=True)
    inquirer_profile = serializers.SerializerMethodField()

    def get_inquirer_profile(self, obj):
        profile, serializer_class = get_role_profile(obj.applicant)
        if profile is None or serializer_class is None:
            return None
        return serializer_class(profile, context=self.context).data

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
            "inquirer_profile",
        ]
        read_only_fields = [
            "applicant",
            "applied_at",
        ]


class InternshipSortApplicationSerializer(BaseModelSerializer):
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
    job_provider_name = serializers.SerializerMethodField()
    education_tags_name = EducationLevelDropdownSerializer(
        source="education_tags", many=True, read_only=True
    )

    job_provider = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(
            user_type__in=["corporate"],
            deleted=False,
        ),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Job
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "name",
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
            "created_by",
            "job_provider",
            "job_provider_name",
            "why_this_match",
            "status",
            "application_deadline",
        ]

    def get_job_provider_name(self, obj):
        if obj.job_provider:
            if hasattr(obj.job_provider, "corporate_profile"):
                name = obj.job_provider.corporate_profile.company_name
                if name:
                    return name
            return obj.job_provider.full_name
        return None

    def validate(self, attrs):
        # New jobs must carry a name; the AI generation payload always includes one.
        if self.instance is None and not str(attrs.get("name") or "").strip():
            raise serializers.ValidationError({"name": "This field is required."})
        return attrs


class JobApplicationSerializer(BaseModelSerializer):
    applicant_name = serializers.CharField(source="applicant.full_name", read_only=True)
    applicant_type = serializers.CharField(source="applicant.user_type", read_only=True)
    job_name = serializers.CharField(source="job.name", read_only=True)
    inquirer_profile = serializers.SerializerMethodField()

    def get_inquirer_profile(self, obj):
        profile, serializer_class = get_role_profile(obj.applicant)
        if profile is None or serializer_class is None:
            return None
        return serializer_class(profile, context=self.context).data

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
            "inquirer_profile",
            "applied_at",
        ]
        read_only_fields = [
            "applicant",
            "applied_at",
        ]


class JobSortApplicationSerializer(BaseModelSerializer):
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


class InternshipApplicationNoteSerializer(BaseModelSerializer):

    class Meta:
        model = InternshipApplicationNote
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "application",
            "note",
        ]
        read_only_fields = ["application"]


class JobApplicationNoteSerializer(BaseModelSerializer):

    class Meta:
        model = JobApplicationNote
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "application",
            "note",
        ]
        read_only_fields = ["application"]
