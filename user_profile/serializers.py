from rest_framework import serializers
from django.utils.timezone import now
from language_master.models import Language
from common.mixins.serializer_mixins import (
    ProfileLanguageMixin,
    ProfileLanguageSaveMixin,
    ProfileLanguageSaveWithTimeMixin,
    ProfileUpdateTimestampMixin,
)
from user_profile.models import (
    BusinessSetting,
    ChildProfile,
    InstituteGallery,
    SchoolCollegeGallery,
    CorporateGallery,
    ParentProfile,
    Profile,
    ProfessionalProfile,
    StudentProfile,
    UserProfile,
)
from common.serializers import BaseModelSerializer
from .models import InstituteProfile, SchoolCollegeProfile, CorporateProfile

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
        queryset=Language.objects.filter(is_active=True, deleted=False),
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
    first_name =serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    profile_image = serializers.CharField(source="user.profile_image", read_only=True)

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
            "first_name",
            "last_name",
            "phone",
            "email",
            "profile_image",
            "created_at",
            "updated_at",
        ]

class StudentProfileUpsertSerializer(ProfileLanguageSaveWithTimeMixin, serializers.ModelSerializer):
    language = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Language.objects.filter(is_active=True, deleted=False),
        required=False,
    )

    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    phone = serializers.CharField(source="user.phone", required=False)
    profile_image = serializers.CharField(source="user.profile_image", required=False)

    class Meta:
        model = StudentProfile
        fields = [
            "first_name",
            "last_name",
            "phone",
            "profile_image",
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

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()
        return super().update(instance, validated_data)

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

    first_name =serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    profile_image = serializers.CharField(source="user.profile_image", read_only=True)

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
            "first_name",
            "last_name",
            "phone",
            "email",
            "profile_image",
            "created_at",
            "updated_at",
        ]


class ProfessionalProfileUpsertSerializer(ProfileLanguageSaveWithTimeMixin, serializers.ModelSerializer):
    language = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Language.objects.filter(is_active=True, deleted=False),
        required=False,
    )

    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    phone = serializers.CharField(source="user.phone", required=False)
    profile_image = serializers.CharField(source="user.profile_image", required=False)

    class Meta:
        model = ProfessionalProfile
        fields = [
            "first_name",
            "last_name",
            "phone",
            "profile_image",
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

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()
        return super().update(instance, validated_data)


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

    first_name =serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    profile_image = serializers.CharField(source="user.profile_image", read_only=True)

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
            "first_name",
            "last_name",
            "phone",
            "email",
            "profile_image",
            "created_at",
            "updated_at",
        ]


class ParentProfileUpsertSerializer(ProfileLanguageSaveWithTimeMixin, serializers.ModelSerializer):
    language = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Language.objects.filter(is_active=True, deleted=False),
        required=False,
    )
    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    phone = serializers.CharField(source="user.phone", required=False)
    profile_image = serializers.CharField(source="user.profile_image", required=False)

    class Meta:
        model = ParentProfile
        fields = [
            "language",
            "relationship",
            "other_relationship_text",
            "first_name",
            "last_name",
            "phone",
            "profile_image",
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
        user_data = validated_data.pop("user", None)
        user = instance.user
        if user_data:
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
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
    language = serializers.SerializerMethodField()

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
            "phone",
            "email",
            "language",
            "career_direction",
            "education",
            "skills",
            "projects",
            "internships",
            "certifications",
            "achievements",
            "extra_activities",
            "additional_insights",
            "preferred_job_locations",
            "linkedin_url",
            "github_url",
            "portfolio",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "parent_profile", "created_at", "updated_at")

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_language(self, obj):
        return [
            {"id": lang.id, "code": lang.code, "name": lang.name}
            for lang in obj.language.all()
        ]


class ChildProfileCreateSerializer(serializers.ModelSerializer):
    language = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Language.objects.filter(is_active=True, deleted=False),
        required=False,
    )

    class Meta:
        model = ChildProfile
        fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "education_level",
            "stream",
            "academic_performance",
            "phone",
            "email",
            "language",
            "career_direction",
            "education",
            "skills",
            "projects",
            "internships",
            "certifications",
            "achievements",
            "extra_activities",
            "additional_insights",
            "preferred_job_locations",
            "linkedin_url",
            "github_url",
            "portfolio",
        ]

    def create(self, validated_data):
        language = validated_data.pop("language", None)
        instance = super().create(validated_data)
        if language is not None:
            instance.language.set(language)
        return instance

    def update(self, instance, validated_data):
        language = validated_data.pop("language", None)
        instance.updated_at = now()
        instance = super().update(instance, validated_data)
        if language is not None:
            instance.language.set(language)
        return instance


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


class InstituteGallerySerializer(BaseModelSerializer):
    class Meta:
        model = InstituteGallery
        fields = BaseModelSerializer.Meta.fields +[
            "id",
            "institute",
            "image",
        ]

class InstituteProfileSerializer(BaseModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    profile_image = serializers.CharField(source="user.profile_image", read_only=True)
    city = serializers.CharField(source="user.city.name", read_only=True)
    state = serializers.CharField(source="user.states.name", read_only=True)
    gallery_images = InstituteGallerySerializer(many=True, read_only=True)

    class Meta:
        model = InstituteProfile
        fields = BaseModelSerializer.Meta.fields +[
            "id",
            "user",
            "student_trained",
            "placements",
            "success_rate",
            "about_us",
            "courses_offered",
            "key_highlights",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            "profile_image",
            "city",
            "state",
            "gallery_images",
        ]

class InstituteProfileUpSerializer(BaseModelSerializer):

    class Meta:
        model = InstituteProfile
        fields = BaseModelSerializer.Meta.fields +[
            "id",
            "user",
            "student_trained",
            "placements",
            "success_rate",
            "about_us",
            "courses_offered",
            "key_highlights",
        ]

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        request = self.context.get("request")
        if request:
            instance.save(user=request.user)
        else:
            instance.save()
        return instance


class SchoolCollegeGallerySerializer(BaseModelSerializer):
    class Meta:
        model = SchoolCollegeGallery
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "school_college",
            "image",
        ]


class SchoolCollegeProfileSerializer(BaseModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    profile_image = serializers.CharField(source="user.profile_image", read_only=True)
    city = serializers.CharField(source="user.city.name", read_only=True)
    state = serializers.CharField(source="user.states.name", read_only=True)
    gallery_images = SchoolCollegeGallerySerializer(many=True, read_only=True)

    class Meta:
        model = SchoolCollegeProfile
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "user",
            "student_trained",
            "placements",
            "success_rate",
            "about_us",
            "courses_offered",
            "key_highlights",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            "profile_image",
            "city",
            "state",
            "gallery_images",
        ]


class SchoolCollegeProfileUpSerializer(BaseModelSerializer):
    class Meta:
        model = SchoolCollegeProfile
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "user",
            "student_trained",
            "placements",
            "success_rate",
            "about_us",
            "courses_offered",
            "key_highlights",
        ]

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        request = self.context.get("request")
        if request:
            instance.save(user=request.user)
        else:
            instance.save()
        return instance


class CorporateGallerySerializer(BaseModelSerializer):
    class Meta:
        model = CorporateGallery
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "corporate",
            "image",
        ]


class CorporateProfileSerializer(BaseModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    profile_image = serializers.CharField(source="user.profile_image", read_only=True)
    city = serializers.CharField(source="user.city.name", read_only=True)
    state = serializers.CharField(source="user.states.name", read_only=True)
    gallery_images = CorporateGallerySerializer(many=True, read_only=True)

    class Meta:
        model = CorporateProfile
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "user",
            "open_job",
            "employees",
            "years_in_business",
            "about_us",
            "perks_benefits",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            "profile_image",
            "city",
            "state",
            "gallery_images",
        ]


class CorporateProfileUpSerializer(BaseModelSerializer):
    class Meta:
        model = CorporateProfile
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "user",
            "open_job",
            "employees",
            "years_in_business",
            "about_us",
            "perks_benefits",
        ]

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        request = self.context.get("request")
        if request:
            instance.save(user=request.user)
        else:
            instance.save()
        return instance

