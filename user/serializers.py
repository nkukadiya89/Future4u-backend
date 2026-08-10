from django.contrib.auth.models import Permission
from rest_framework import serializers

from common.mixins.serializer_mixins import (
    DeletedFieldsMixin,
    OtpEmailValidationMixin,
    UserNameMixin,
)
from user.models import CustomGroup, RoleFamily, User
from user.user_auth import get_user_groups, get_user_permissions
from utils.datetime_formatter import format_datetime


class CustomGroupSerializers(serializers.ModelSerializer):
    sequence = serializers.IntegerField(read_only=True)
    name = serializers.CharField(source="group_name", read_only=True)

    class Meta:
        model = CustomGroup
        fields = [
            "id",
            "name",
            "company",
            "sequence",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "deleted",
        ]
        # Ownership, soft-delete and company scoping are server-managed.
        read_only_fields = [
            "company",
            "created_by",
            "updated_by",
            "deleted",
        ]


class PermissionSerializers(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)
    model_name = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "app_label", "model_name"]


class VerifyAccountSerializer(OtpEmailValidationMixin, serializers.ModelSerializer):
    otp = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["email", "otp"]


class VerifyOTPSerializer(OtpEmailValidationMixin, serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()

    class Meta:
        model = User
        fields = [
            "email",
            "otp",
        ]


class LoginWithEmailOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_null=True)
    otp_method = serializers.CharField(required=True)
    phone = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["email", "phone", "otp_method"]


class VerifyLoginWithEmailOtpSerializer(serializers.Serializer):
    email = serializers.CharField(required=False, allow_null=True)
    phone = serializers.IntegerField(required=False, allow_null=True)
    otp = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = User
        fields = ["email", "phone", "otp"]


class UserSerializer(serializers.ModelSerializer):
    education_level = serializers.SerializerMethodField()
    stream = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "phone", "education_level", "stream"]

    def get_education_level(self, obj):
        if obj.user_type == obj.Role.STUDENT:
            student_profile = getattr(obj, "student_profile", None)
            return (
                getattr(student_profile, "education_level_id", None)
                if student_profile
                else None
            )
        return None

    def get_stream(self, obj):
        if obj.user_type == obj.Role.STUDENT:
            student_profile = getattr(obj, "student_profile", None)
            return (
                getattr(student_profile, "stream_id", None) if student_profile else None
            )
        return None


class RoleFamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleFamily
        fields = ["id", "family_name", "created_by", "updated_by"]

        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }


class UserDetailsSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="id", required=False)

    class Meta:
        model = User
        fields = [
            "user_id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "about_me",
            "designation",
            "profile_image",
            "country",
            "states",
            "city",
            "address",
        ]
        extra_kwargs = {
            "email": {"read_only": True},
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        company_profile_counts = [
            {
                "company": 0,
                "company_perc": 0,
                "company_material_perc": 0,
                "site_location_perc": 0,
                "user_role_perc": 0,
                "employee_perc": 0,
                "pr_release_perc": 0,
                "business_setting_perc": 0,
                "vendor_perc": 0,
            }
        ]
        company_profile_perc = 0

        company_role = None
        vendor_role = None

        assign_site_employee = []

        ret["assign_site_employee"] = assign_site_employee
        # Translate internal Django groups to the canonical role shape.
        ret["role"] = [
            {"role_id": group["id"], "role_name": group["name"]}
            for group in get_user_groups(instance)
        ]

        ret["company_role"] = company_role
        ret["vendor_role"] = vendor_role
        ret["permission"] = get_user_permissions(instance)
        ret["keep_me_logged_in"] = instance.keep_me_logged_in

        return ret


class UserQuickSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "full_name"]

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserListSerializer(
    DeletedFieldsMixin, UserNameMixin, serializers.ModelSerializer
):
    country_name = serializers.SerializerMethodField(read_only=True)
    state_name = serializers.SerializerMethodField(read_only=True)
    city_name = serializers.SerializerMethodField(read_only=True)
    date_joined = serializers.SerializerMethodField(read_only=True)
    last_login = serializers.SerializerMethodField(read_only=True)
    password_last_changed = serializers.SerializerMethodField(read_only=True)
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    deleted_by_name = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "about_me",
            "phone",
            "profile_image",
            "designation",
            "user_type",
            "status",
            "is_active",
            "is_staff",
            "is_superuser",
            "email_verified",
            "keep_me_logged_in",
            "terms_accepted",
            "referral_code",
            "date_joined",
            "last_login",
            "password_last_changed",
            "country",
            "country_name",
            "states",
            "state_name",
            "city",
            "city_name",
            "address",
            "must_change_password",
            "created_by",
            "created_at",
            "updated_by",
            "updated_by_name",
            "updated_at",
            "deleted",
            "deleted_at",
            "deleted_by",
            "deleted_by_name",
        ]

    def get_country_name(self, obj):
        return obj.country.name if obj.country_id else None

    def get_state_name(self, obj):
        return obj.states.name if obj.states_id else None

    def get_city_name(self, obj):
        return obj.city.name if obj.city_id else None

    def get_date_joined(self, obj):
        return format_datetime(getattr(obj, "date_joined", None))

    def get_last_login(self, obj):
        return format_datetime(getattr(obj, "last_login", None))

    def get_password_last_changed(self, obj):
        return format_datetime(getattr(obj, "password_last_changed", None))

    def get_created_at(self, obj):
        return format_datetime(getattr(obj, "created_at", None))

    def get_updated_at(self, obj):
        return format_datetime(getattr(obj, "updated_at", None))
