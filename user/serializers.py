from django.contrib.auth.models import Group, Permission
from rest_framework import serializers

from company.models import CompanyProfile
from user.models import ContentTypeModel, CustomGroup, RoleFamily, User
from user.user_auth import get_user_groups, get_user_permissions


class CustomGroupSerializers(serializers.ModelSerializer):
    sequence = serializers.IntegerField(source="customgroup.sequence", read_only=True)
    name = serializers.CharField(source="customgroup.group_name", read_only=True)

    class Meta:
        model = CustomGroup
        fields = [
            "id",
            "name",
            "company",
            "vendor",
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
        if data["otp"] != str(query.otp):  # type: ignore
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
        query = User.objects.get(email=email)
        if data["otp"] != str(query.otp):
            raise serializers.ValidationError("OTP is incorrect")
        return data


class LoginWithEmailOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_null=True)
    otp_method = serializers.CharField(required=True)
    whatsapp_verified = serializers.BooleanField()
    phone = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["email", "phone", "otp_method", "whatsapp_verified"]


class VerifyLoginWithEmailOtpSerializer(serializers.Serializer):
    email = serializers.CharField(required=False, allow_null=True)
    phone = serializers.IntegerField(required=False, allow_null=True)
    otp = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = User
        fields = ["email", "phone", "otp"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "phone"]


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
        ]

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

        if instance.company:
            company_role = Group.objects.get(name="Company Admin").name
            try:
                company_profile = CompanyProfile.objects.get(
                    company=instance.company.id
                )
                company_profile_count = [
                    {
                        "company": company_profile.company.id,  # type: ignore
                        "company_perc": company_profile.company_perc,
                        "company_material_perc": company_profile.company_material_perc,
                        "site_location_perc": company_profile.site_location_perc,
                        "user_role_perc": company_profile.user_role_perc,
                        "employee_perc": company_profile.employee_perc,
                        "pr_release_perc": company_profile.pr_release_perc,
                        "business_setting_perc": company_profile.business_setting_perc,
                        "vendor_perc": company_profile.vendor_perc,
                    }
                ]
                company_profile_perc = (
                    company_profile.company_perc
                    + company_profile.company_material_perc
                    + company_profile.site_location_perc
                    + company_profile.user_role_perc
                    + company_profile.employee_perc
                    + company_profile.pr_release_perc
                    + company_profile.business_setting_perc
                    + company_profile.vendor_perc
                )
                ret["company_profile_count"] = company_profile_count
                ret["company_profile_perc"] = company_profile_perc

            except CompanyProfile.DoesNotExist:
                ret["company_profile_count"] = company_profile_counts
                ret["company_profile_perc"] = company_profile_perc

        elif instance.vendor:
            vendor_role = Group.objects.get(name="Vendor Admin").name
            ret["company_profile_count"] = company_profile_counts
            ret["company_profile_perc"] = company_profile_perc

        if instance.employee is not None:
            assign_site_employee = [
                {
                    "id": site.id,
                    "name": site.site_name,
                }
                for site in instance.employee.assign_site_employee.all()
            ]
        else:
            assign_site_employee = []

        ret["company"] = instance.company.id if instance.company else None
        ret["vendor"] = instance.vendor.id if instance.vendor else None
        ret["employee"] = instance.employee.id if instance.employee else None
        ret["assign_site_employee"] = assign_site_employee
        ret["role"] = get_user_groups(instance)

        ret["company_role"] = company_role
        ret["vendor_role"] = vendor_role
        ret["permission"] = get_user_permissions(instance)
        ret["keep_me_logged_in"] = instance.keep_me_logged_in

        return ret
