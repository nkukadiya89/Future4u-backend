from rest_framework import serializers

from user_profile.models import BusinessSetting, UserProfile

# Derive valid sets directly from model TextChoices — single source of truth
VALID_CONCERNS = {c.value for c in UserProfile.UserConcern}
VALID_INTEREST_CATEGORIES = {c.value for c in UserProfile.InterestCategory}
VALID_CAREER_VALUES = {c.value for c in UserProfile.CareerValue}
VALID_PLATFORM_GOALS = {c.value for c in UserProfile.PlatformGoal}


def validate_json_choices(value, valid_set, field_name):
    if not isinstance(value, list):
        raise serializers.ValidationError({field_name: "Must be a list."})
    invalid = [v for v in value if v not in valid_set]
    if invalid:
        raise serializers.ValidationError({field_name: f"Invalid values: {invalid}. Allowed: {sorted(valid_set)}"})
    return value



class UserProfileSerializer(serializers.ModelSerializer):
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
    country_name = serializers.CharField(
        source="country.name", read_only=True, default=None
    )
    state_name = serializers.CharField(
        source="state.name", read_only=True, default=None
    )
    city_name = serializers.CharField(
        source="city.name", read_only=True, default=None
    )
    language = serializers.SerializerMethodField()

    def get_language(self, obj):
        return [{"id": str(l.id), "name": l.name, "code": l.code} for l in obj.language.all()]

    class Meta:
        model = UserProfile
        fields = [
            "id", "user",
            "role",
            "language", "medium",
            "country", "country_name",
            "state", "state_name",
            "city", "city_name",
            "education_level", "education_level_code", "education_level_name",
            "stream", "stream_code", "stream_name",
            "interest_categories",
            "career_goal",
            "science_track",
            "parent_support_level",
            "user_concerns",
            "career_values",
            "platform_goals",
        ]


class UserProfileUpsertSerializer(serializers.ModelSerializer):
    language = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=__import__('language_master.models', fromlist=['Language']).Language.objects.filter(is_active=True, deleted=False),
        required=False,
    )

    class Meta:
        model = UserProfile
        fields = ["role", "language", "medium", "country", "state", "city", "education_level", "stream", "interest_categories", "career_goal", "science_track", "parent_support_level", "user_concerns", "career_values", "platform_goals"]

    def validate_user_concerns(self, value):
        return validate_json_choices(value, VALID_CONCERNS, "user_concerns")

    def validate_interest_categories(self, value):
        return validate_json_choices(value, VALID_INTEREST_CATEGORIES, "interest_categories")

    def validate_career_values(self, value):
        return validate_json_choices(value, VALID_CAREER_VALUES, "career_values")

    def validate_platform_goals(self, value):
        return validate_json_choices(value, VALID_PLATFORM_GOALS, "platform_goals")

    def update(self, instance, validated_data):
        language = validated_data.pop("language", None)
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
