from datetime import timedelta

from django.apps import apps as django_apps
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from activity_log.services import log_event
from company.models import Company
from employee.models import Employee
from user.models import User


# Exclude Django's own framework apps from permission claims; app-label
# filtering is stable across databases (content-type ids differ on fresh installs).
PROJECT_APP_LABELS = sorted(
    app_config.label
    for app_config in django_apps.get_app_configs()
    if not app_config.name.startswith("django.")
)


def get_user_permissions(user):
    user_permissions = Permission.objects.filter(user=user)
    custom_group_permissions = Permission.objects.filter(
        group__user=user, content_type__app_label__in=PROJECT_APP_LABELS
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
    custom_group_permissions = Permission.objects.filter(
        group__user=user, content_type__app_label__in=PROJECT_APP_LABELS
    ).distinct()

    all_permissions_set = {
        f"{perm.content_type.app_label}|{perm.codename}"
        for perm in custom_group_permissions
    }

    all_permissions = sorted(list(all_permissions_set))

    return all_permissions


def get_user_groups(user):
    groups = Group.objects.filter(user=user)
    group_data = [{"id": group.id, "name": group.name} for group in groups]
    return group_data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "email" in self.fields:
            self.fields["email"].required = False
        self.fields["username"] = serializers.CharField(required=False)

    def validate(self, attrs):
        request_data = self.context["request"].data
        raw_login = (
            request_data.get("username") or attrs.get("username") or attrs.get("email")
        )

        if not raw_login:
            raise AuthenticationFailed(
                {"success": False, "message": "Username and password are required"}
            )

        login_value = str(raw_login).strip()

        keep_me_logged = self.context["request"].data.get("keep_me_logged_in", False)

        if "@" in login_value and "." in login_value:
            user = User.objects.filter(email=login_value).first()
            if user is None:
                raise AuthenticationFailed(
                    {
                        "success": False,
                        "message": "Email is incorrect",
                    }
                )
        else:
            user = User.objects.filter(phone=login_value).first()
            if user is None:
                raise AuthenticationFailed(
                    {
                        "success": False,
                        "message": "Mobile number is incorrect",
                    }
                )

        if user is None:
            raise AuthenticationFailed(
                {
                    "success": False,
                    "message": "No active account found with the given credentials",
                }
            )

        if user.deleted:
            raise AuthenticationFailed(
                {
                    "success": False,
                    "message": "User account has been deleted. Please contact administrator.",
                }
            )

        if not user.is_active:
            raise AuthenticationFailed(
                {
                    "success": False,
                    "message": "User account is not active. Please contact administrator.",
                }
            )

        attrs["email"] = user.email
        try:
            token = super(CustomTokenObtainPairSerializer, self).validate(attrs)
        except AuthenticationFailed as e:
            # The user was already resolved above, so this is a bad password.
            error_detail = str(e.detail).lower()
            if (
                "authentication failed" in error_detail
                or "invalid password" in error_detail
                or "no active account found" in error_detail
                or "invalid credentials" in error_detail
            ):
                raise AuthenticationFailed(
                    {
                        "success": False,
                        "message": "Password is incorrect",
                    }
                )
            else:
                raise e

        permission_data = get_user_permissions(user)
        group_permission_data = get_user_group_permissions(user)

        token.update(
            {
                "userData": {
                    "user_id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "user_type": user.user_type,
                    "permission": permission_data,
                    "role_permission": group_permission_data,
                    "keep_me_logged_in": keep_me_logged,
                    "last_login": user.last_login,
                    "must_change_password": user.must_change_password,
                }
            }
        )

        if keep_me_logged:
            access_token = AccessToken(token["access"])
            refresh_token = RefreshToken(token["refresh"])

            access_token.set_exp(lifetime=timedelta(days=365))
            refresh_token.set_exp(lifetime=timedelta(days=365))

            token["access"] = str(access_token)
            token["refresh"] = str(refresh_token)

        user.keep_me_logged_in = keep_me_logged
        user.last_login = now()
        user.save()

        log_event(
            event="auth.login",
            description="Logged in",
            user=user,
            entity_type="user",
            entity_id=user.id,
            metadata={
                "user_type": user.user_type,
                "keep_me_logged_in": keep_me_logged,
            },
            request=self.context.get("request"),
        )

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
