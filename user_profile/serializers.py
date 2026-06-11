from rest_framework import serializers

from common.mixins.serializer_mixins import (
    ProfileLanguageMixin,
    ProfileLanguageSaveMixin,
    ProfileLanguageSaveWithTimeMixin,
    ProfileUpdateTimestampMixin,
)
from user_profile.models import (
    BusinessSetting,
    ParentProfile,
    ProfessionalProfile,
    StudentProfile,
    UserProfile,
)

from user_profile.models import (
    BusinessSetting,
    # InternshipApplication,
    # InternshipProfile,
    Profile,
    UserProfile,
)


def validate_json_choices(value, valid_set, field_name):
    if not isinstance(value, list):
        raise serializers.ValidationError({field_name: "Must be a list."})
    invalid = [v for v in value if v not in valid_set]
    if invalid:
        raise serializers.ValidationError(
            {field_name: f"Invalid values: {invalid}. Allowed: {sorted(valid_set)}"}
        )
    return value


class UserProfileSerializer(ProfileLanguageMixin, serializers.ModelSerializer):
    """Base profile serializer for Super Admin with language preference"""

    role = serializers.CharField(source="user.user_type", read_only=True)
    language = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user",
            "role",
            "language",
        ]


class UserProfileUpsertSerializer(ProfileLanguageSaveMixin, serializers.ModelSerializer):
    """Base profile upsert serializer for Super Admin"""

    language = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=__import__(
            "language_master.models", fromlist=["Language"]
        ).Language.objects.filter(is_active=True, deleted=False),
        required=False,
    )

    class Meta:
        model = UserProfile
        fields = [
            "language",
        ]


class StudentProfileSerializer(ProfileLanguageMixin, ProfileUpdateTimestampMixin, serializers.ModelSerializer):
    """Student-specific profile serializer with language and educational fields"""

    role = serializers.CharField(source="user.user_type", read_only=True)
    education_level_code = serializers.CharField(
        source="education_level.level_code", read_only=True, default=None
    )
    education_level_name = serializers.CharField(
        source="education_level.display_name", read_only=True, default=None
    )
    stream_code = serializers.CharField(
        source="stream.stream_code", read_only=True, default=None
    )
    stream_name = serializers.CharField(
        source="stream.stream_name", read_only=True, default=None
    )
    language = serializers.SerializerMethodField()
    # Location fields from User model
    country = serializers.IntegerField(
        source="user.country.id", read_only=True, default=None
    )
    country_name = serializers.CharField(
        source="user.country.name", read_only=True, default=None
    )
    state = serializers.IntegerField(
        source="user.states.id", read_only=True, default=None
    )
    state_name = serializers.CharField(
        source="user.states.name", read_only=True, default=None
    )
    city = serializers.IntegerField(source="user.city.id", read_only=True, default=None)
    city_name = serializers.CharField(
        source="user.city.name", read_only=True, default=None
    )

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "user",
            "role",
            "language",
            "country",
            "country_name",
            "state",
            "state_name",
            "city",
            "city_name",
            "science_track",
            "medium",
            "education_level",
            "education_level_code",
            "education_level_name",
            "stream",
            "stream_code",
            "stream_name",
            "career_direction",
            "education",
            "skills",
            "projects",
            "internships",
            "certifications",
            "achievements",
            "extra_activities",
            "additional_insights",
            "linkedin_url",
            "github_url",
            "portfolio",
            "created_at",
            "updated_at",
        ]


class StudentProfileUpsertSerializer(ProfileLanguageSaveWithTimeMixin, serializers.ModelSerializer):
    language = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=__import__(
            "language_master.models", fromlist=["Language"]
        ).Language.objects.filter(is_active=True, deleted=False),
        required=False,
    )

    class Meta:
        model = StudentProfile
        fields = [
            "language",
            "science_track",
            "medium",
            "education_level",
            "stream",
            "career_direction",
            "education",
            "skills",
            "projects",
            "internships",
            "certifications",
            "achievements",
            "extra_activities",
            "additional_insights",
            "linkedin_url",
            "github_url",
            "portfolio",
        ]


class BusinessSettingSerializer(serializers.ModelSerializer):

    class Meta:
        model = BusinessSetting
        fields = [
            "id",
            "company",
            "user_id",
            "notifications",
            "sgst",
            "cgst",
            "igst",
            "country",
            "state",
            "city",
            "currency",
            "created_by",
            "updated_by",
        ]

        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def to_representation(self, instance):
        response_data = super().to_representation(instance)
        return response_data

    # Helper Function to reduce fetching instances
    def get_instance(self, model, id, error_message):
        try:
            return model.objects.get(id=id)
        except model.DoesNotExist:
            raise serializers.ValidationError(
                {"success": False, "message": error_message}
            )

    def update(self, instance, validated_data):
        # Update instance attributes with validated data
        instance.company = validated_data.get("company", instance.company)
        instance.notifications = validated_data.get(
            "notifications", instance.notifications
        )
        instance.sgst = validated_data.get("sgst", instance.sgst)
        instance.cgst = validated_data.get("cgst", instance.cgst)
        instance.igst = validated_data.get("igst", instance.igst)
        instance.country = validated_data.get("country", instance.country)
        instance.state = validated_data.get("state", instance.state)
        instance.city = validated_data.get("city", instance.city)
        instance.currency = validated_data.get("currency", instance.currency)

        # Save instance
        instance.save()
        return instance


class ProfessionalProfileSerializer(ProfileLanguageMixin, ProfileUpdateTimestampMixin, serializers.ModelSerializer):
    """Working Professional-specific profile serializer matching StudentProfile pattern"""

    role = serializers.CharField(source="user.user_type", read_only=True)
    education_level_code = serializers.CharField(
        source="education_level.level_code", read_only=True, default=None
    )
    education_level_name = serializers.CharField(
        source="education_level.display_name", read_only=True, default=None
    )
    language = serializers.SerializerMethodField()
    # Location fields from User model
    country = serializers.IntegerField(
        source="user.country.id", read_only=True, default=None
    )
    country_name = serializers.CharField(
        source="user.country.name", read_only=True, default=None
    )
    state = serializers.IntegerField(
        source="user.states.id", read_only=True, default=None
    )
    state_name = serializers.CharField(
        source="user.states.name", read_only=True, default=None
    )
    city = serializers.IntegerField(source="user.city.id", read_only=True, default=None)
    city_name = serializers.CharField(
        source="user.city.name", read_only=True, default=None
    )

    class Meta:
        model = ProfessionalProfile
        fields = [
            "id",
            "user",
            "role",
            "language",
            "country",
            "country_name",
            "state",
            "state_name",
            "city",
            "city_name",
            "employment_type",
            "years_of_experience",
            "education_level",
            "education_level_code",
            "education_level_name",
            "current_job_title",
            "current_industry",
            "company_size",
            "career_direction",
            "education",
            "work_experience",
            "skills",
            "certifications",
            "key_highlights",
            "additional_insights",
            "linkedin_url",
            "github_url",
            "portfolio",
            "created_at",
            "updated_at",
        ]


class ProfessionalProfileUpsertSerializer(ProfileLanguageSaveWithTimeMixin, serializers.ModelSerializer):
    language = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=__import__(
            "language_master.models", fromlist=["Language"]
        ).Language.objects.filter(is_active=True, deleted=False),
        required=False,
    )

    class Meta:
        model = ProfessionalProfile
        fields = [
            "language",
            "employment_type",
            "years_of_experience",
            "education_level",
            "current_job_title",
            "current_industry",
            "company_size",
            "career_direction",
            "education",
            "work_experience",
            "skills",
            "certifications",
            "key_highlights",
            "additional_insights",
            "linkedin_url",
            "github_url",
            "portfolio",
        ]


class ParentProfileSerializer(ProfileLanguageMixin, ProfileUpdateTimestampMixin, serializers.ModelSerializer):
    """Parent-specific profile serializer"""

    role = serializers.CharField(source="user.user_type", read_only=True)
    language = serializers.SerializerMethodField()
    child_education_level_name = serializers.CharField(
        source="child_education_level.display_name", read_only=True, default=None
    )
    stream_name = serializers.CharField(
        source="stream.stream_name", read_only=True, default=None
    )
    # Location fields from User model
    country = serializers.IntegerField(
        source="user.country.id", read_only=True, default=None
    )
    country_name = serializers.CharField(
        source="user.country.name", read_only=True, default=None
    )
    state = serializers.IntegerField(
        source="user.states.id", read_only=True, default=None
    )
    state_name = serializers.CharField(
        source="user.states.name", read_only=True, default=None
    )
    city = serializers.IntegerField(source="user.city.id", read_only=True, default=None)
    city_name = serializers.CharField(
        source="user.city.name", read_only=True, default=None
    )

    class Meta:
        model = ParentProfile
        fields = [
            "id",
            "user",
            "role",
            "language",
            "country",
            "country_name",
            "state",
            "state_name",
            "city",
            "city_name",
            "relationship",
            "child_name",
            "child_education_level",
            "child_education_level_name",
            "stream",
            "stream_name",
            "academic_performance",
            "created_at",
            "updated_at",
        ]


class ParentProfileUpsertSerializer(ProfileLanguageSaveWithTimeMixin, serializers.ModelSerializer):
    language = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=__import__(
            "language_master.models", fromlist=["Language"]
        ).Language.objects.filter(is_active=True, deleted=False),
        required=False,
    )
    child_education_level = serializers.PrimaryKeyRelatedField(
        queryset=__import__(
            "education_level.models", fromlist=["EducationLevel"]
        ).EducationLevel.objects.filter(is_active=True, deleted=False),
        required=False,
    )
    stream = serializers.PrimaryKeyRelatedField(
        queryset=__import__("stream.models", fromlist=["Stream"]).Stream.objects.filter(
            is_active=True, deleted=False
        ),
        required=False,
    )

    class Meta:
        model = ParentProfile
        fields = [
            "language",
            "relationship",
            "child_name",
            "child_education_level",
            "stream",
            "academic_performance",
        ]


class BusinessSettingInfoSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", required=False)
    country_name = serializers.CharField(
        source="country.name", required=False, allow_null=True
    )
    state_name = serializers.CharField(
        source="state.name", required=False, allow_null=True
    )
    city_name = serializers.CharField(
        source="city.name", required=False, allow_null=True
    )

    class Meta:
        model = BusinessSetting
        fields = [
            "id",
            "company",
            "company_name",
            "notifications",
            "sgst",
            "cgst",
            "igst",
            "country",
            "country_name",
            "state",
            "state_name",
            "city",
            "city_name",
            "currency",
        ]


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = "__all__"
        read_only_fields = [
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "deleted",
        ]
