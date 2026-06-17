from rest_framework import serializers
from django.utils.timezone import now

from common.mixins.serializer_mixins import (
    ProfileLanguageMixin,
    ProfileLanguageSaveMixin,
    ProfileLanguageSaveWithTimeMixin,
    ProfileUpdateTimestampMixin,
)
from user_profile.models import (
    BusinessSetting,
    ChildProfile,
    ParentProfile,
    Profile,
    ProfessionalProfile,
    StudentProfile,
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
            "other_relationship_text",
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

    class Meta:
        model = ParentProfile
        fields = [
            "language",
            "relationship",
            "other_relationship_text",
        ]

    def validate(self, attrs):
        relationship = attrs.get(
            "relationship",
            getattr(self.instance, "relationship", None),
        )
        other_text = attrs.get(
            "other_relationship_text",
            getattr(self.instance, "other_relationship_text", ""),
        )

        if not relationship:
            raise serializers.ValidationError(
                {"relationship": "This field is required."}
            )

        if relationship == ParentProfile.Relationship.OTHER and not (
            other_text or ""
        ).strip():
            raise serializers.ValidationError(
                {
                    "other_relationship_text": (
                        "This field is required when relationship is other."
                    )
                }
            )

        if relationship != ParentProfile.Relationship.OTHER:
            attrs["other_relationship_text"] = ""

        return attrs

    def update(self, instance, validated_data):
        language = validated_data.pop("language", None)
        instance.updated_at = now()
        instance = super().update(instance, validated_data)
        if language is not None:
            instance.language.set(language)
        return instance

    def create(self, validated_data):
        language = validated_data.pop("language", None)
        instance = super().create(validated_data)
        if language is not None:
            instance.language.set(language)
        return instance


class ChildProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
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

    class Meta:
        model = ChildProfile
        fields = [
            "id",
            "parent_profile",
            "full_name",
            "first_name",
            "last_name",
            "profile_image",
            "date_of_birth",
            "education_level",
            "education_level_code",
            "education_level_name",
            "stream",
            "stream_code",
            "stream_name",
            "academic_performance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "parent_profile", "created_at", "updated_at")

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class ChildProfileCreateSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False, write_only=True)

    class Meta:
        model = ChildProfile
        fields = [
            "first_name",
            "last_name",
            "profile_image",
            "date_of_birth",
            "education_level",
            "stream",
            "academic_performance",
        ]

    def create(self, validated_data):
        validated_data.pop("profile_image", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("profile_image", None)
        instance.updated_at = now()
        return super().update(instance, validated_data)


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
