from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.utils.timezone import now
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from company.models import Company, CompanyProfile
from user.models import User


def get_user_permissions(user):
    user_permissions = Permission.objects.filter(user=user)
    custom_group_permissions = Permission.objects.filter(
        group__user=user, content_type_id__gt=5
    )

    all_permissions_set = {
        f"{perm.content_type.app_label}|{perm.codename}" for perm in user_permissions
    } | {
        f"{perm.content_type.app_label}|{perm.codename}"
        for perm in custom_group_permissions
    }

    all_permissions = sorted(list(all_permissions_set))

    return all_permissions


def get_user_group_permissions(user):
    user_group = Group.objects.filter(user=user).first()

    custom_group_permissions = Permission.objects.filter(
        group=user_group, content_type_id__gt=5
    )

    all_permissions_set = {
        f"{perm.content_type.app_label}|{perm.codename}"
        for perm in custom_group_permissions
    }

    all_permissions = sorted(list(all_permissions_set))

    return all_permissions


def get_user_groups(user):
    groups = Group.objects.filter(user=user)
    group_data = [
        {"id": group.id, "name": group.name} for group in groups  # type: ignore
    ]
    return group_data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Get the provided login value (email or phone)
        login_value = attrs.get("email").lower()  # type: ignore

        keep_me_logged = self.context["request"].data.get("keep_me_logged_in", False)

        # Check if the provided input contains "@" (likely an email)
        if "@" in login_value and "." in login_value:
            user = User.objects.filter(email=login_value).first()

        else:
            # Assuming phone is unique, if not, adjust the query accordingly
            user = User.objects.filter(phone=login_value).first()

        if user is None:
            raise AuthenticationFailed(
                {
                    "success": False,
                    "message": "No active account found with the given credentials",
                }
            )

        attrs["email"] = user.email
        token = super(CustomTokenObtainPairSerializer, self).validate(attrs)

        permission_data = get_user_permissions(user)
        group_permission_data = get_user_group_permissions(user)
        group_data = get_user_groups(user)

        rfq_re_float = None
        company_role = None
        vendor_role = None
        company_profile_perc = 0
        company_profile_count = None
        company_expiry_date = None
        company_active_subscription = None
        company_days_to_expire = None

        if user.company_id:  # type: ignore
            company_role = Group.objects.get(name="Company Admin").name
            try:
                company_profile = CompanyProfile.objects.get(
                    company=user.company_id  # type: ignore
                )
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

            except CompanyProfile.DoesNotExist:
                pass

            company_details = (
                Company.objects.filter(id=user.company_id)  # type: ignore
                .values("active_subscription", "expiry_date", "days_to_expire")
                .first()
                or {}
            )

            company_active_subscription = company_details.get(
                "active_subscription", None
            )
            company_expiry_date = company_details.get("expiry_date", None)
            company_days_to_expire = company_details.get("days_to_expire", None)
        elif user.vendor_id:
            vendor_role = Group.objects.get(name="Vendor Admin").name

        token.update(
            {
                "userData": {  # type: ignore
                    "user_id": user.id,  # type: ignore
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "company_profile_count": company_profile_count,
                    "company_profile_perc": company_profile_perc,
                    "rfq_re_float": rfq_re_float.rfq_re_float if rfq_re_float else None,
                    "company": user.company_id,  # type: ignore
                    "active_subscription": company_active_subscription,
                    "expiry_date": company_expiry_date,
                    "days_to_expire": company_days_to_expire,
                    "vendor": user.vendor_id,
                    "role": group_data,
                    "company_role": company_role,
                    "vendor_role": vendor_role,
                    "permission": permission_data,
                    "group_permission": group_permission_data,
                    "keep_me_logged_in": keep_me_logged,
                    "last_login": user.last_login,
                }
            }
        )  # type: ignore
        if keep_me_logged:
            access_token = AccessToken(token["access"])  # type: ignore
            refresh_token = RefreshToken(token["refresh"])  # type: ignore

            # Set custom lifetime
            access_token.set_exp(lifetime=timedelta(days=365))
            refresh_token.set_exp(lifetime=timedelta(days=365))

            token["access"] = str(access_token)
            token["refresh"] = str(refresh_token)

        user.keep_me_logged_in = keep_me_logged
        user.last_login = now()
        user.save()

        data = {
            "success": True,
            "message": "Login Successful",
            "data": token,
        }

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def get_auth_token(self, user):
        refresh = RefreshToken.for_user(user)
        token = str(refresh.access_token)
        return token
