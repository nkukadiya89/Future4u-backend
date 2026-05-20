from django.contrib.auth.models import Group, Permission
from rest_framework import serializers

from user.models import ContentTypeModel, CustomGroup, RoleFamily, User
from user.user_auth import get_user_groups, get_user_permissions


class CustomGroupSerializers(serializers.ModelSerializer):
    sequence = serializers.IntegerField(source="sequence", read_only=True)
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


class ContentTypeSerializers(serializers.ModelSerializer):
    permission_on = serializers.CharField(source="model")

    class Meta:
        model = ContentTypeModel
        fields = ["id", "permission_on"]


class PermissionSerializers(serializers.ModelSerializer):
    model_name = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "content_type", "model_name"]

    def get_model_name(self, obj):
        model_name = obj.content_type.model.capitalize()
        return model_name


class VerifyAccountSerializer(serializers.ModelSerializer):
    otp = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["email", "otp"]

    def validate(self, data):
        email = data["email"]
        query = User.objects.filter(email=email).first()
        if query is None:
            raise serializers.ValidationError("User not found")
        if data.get("otp") != str(query.otp):  # type: ignore
            raise serializers.ValidationError("OTP is incorrect")
        return data


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()

    class Meta:
        model = User
        fields = [
            "email",
            "otp",
        ]

    def validate(self, data):
        email = data["email"]
        query = User.objects.filter(email=email).first()
        if query is None:
            raise serializers.ValidationError("User not found")
        if data.get("otp") != str(query.otp):
            raise serializers.ValidationError("OTP is incorrect")
        return data


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

        # ret["company"] = instance.company.id if instance.company else None  # Removed
        ret["assign_site_employee"] = assign_site_employee
        ret["role"] = get_user_groups(instance)

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
