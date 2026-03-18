from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from company.models import Company
from employee.models import Employee
from user.models import User


def get_user_permissions(user):
    user_permissions = Permission.objects.filter(user=user)
    custom_group_permissions = Permission.objects.filter(group__user=user, content_type_id__gt=5)

    all_permissions_set = {f"{perm.content_type.app_label}|{perm.codename}" for perm in user_permissions} | {
        f"{perm.content_type.app_label}|{perm.codename}" for perm in custom_group_permissions
    }

    all_permissions = sorted(list(all_permissions_set))

    return all_permissions


def get_user_group_permissions(user):
    user_group = Group.objects.filter(user=user).first()

    custom_group_permissions = Permission.objects.filter(group=user_group, content_type_id__gt=5)

    all_permissions_set = {f"{perm.content_type.app_label}|{perm.codename}" for perm in custom_group_permissions}

    all_permissions = sorted(list(all_permissions_set))

    return all_permissions


def get_user_groups(user):
    groups = Group.objects.filter(user=user)
    group_data = [{"id": group.id, "name": group.name} for group in groups]
    return group_data


# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Make original username field (email) optional and add a common `username` field
#         if "email" in self.fields:
#             self.fields["email"].required = False
#         self.fields["username"] = serializers.CharField(required=False)

#     def validate(self, attrs):
#         # Accept a single common field `login` (email or mobile/phone)
#         request_data = self.context["request"].data
#         raw_login = request_data.get("username") or attrs.get("username") or attrs.get("email")

#         if not raw_login:
#             raise AuthenticationFailed({"success": False, "message": "Username and password are required"})

#         login_input = str(raw_login).strip()

#         keep_me_logged = self.context["request"].data.get("keep_me_logged_in", False)

#         # Determine whether the login is email or phone
#         if "@" in login_input and "." in login_input:
#             user = User.objects.filter(email__iexact=login_input).first()

#         else:
#             user = User.objects.filter(phone=login_input).first()

#         if user is None:
#             raise AuthenticationFailed(
#                 {
#                     "success": False,
#                     "message": "No active account found with the given credentials",
#                 }
#             )

#         attrs["email"] = user.email
#         token = super(CustomTokenObtainPairSerializer, self).validate(attrs)

#         permission_data = get_user_permissions(user)
#         group_permission_data = get_user_group_permissions(user)
#         group_data = get_user_groups(user)

#         company_role = None
#         company_expiry_date = None
#         company_active_subscription = None
#         company_days_to_expire = None

#         # Check if user is Company Admin
#         is_company_admin = any(group.get("name") == "Company Admin" for group in group_data)

#         if user.company_id and is_company_admin:
#             company_role = Group.objects.get(name="Company Admin").name

#             company_details = (
#                 Company.objects.filter(id=user.company_id)
#                 .values("active_subscription", "expiry_date", "days_to_expire")
#                 .first()
#                 or {}
#             )

#             company_active_subscription = company_details.get("active_subscription", None)
#             company_expiry_date = company_details.get("expiry_date", None)
#             company_days_to_expire = company_details.get("days_to_expire", None)

#         token.update(
#             {
#                 "userData": {
#                     "user_id": user.id,
#                     "email": user.email,
#                     "first_name": user.first_name,
#                     "last_name": user.last_name,
#                     "phone": user.phone,
#                     "company": user.company_id if is_company_admin else None,
#                     "company_name": user.company.name if (user.company and is_company_admin) else None,
#                     "partner_company": user.partner_company_id,
#                     "partner_company_name": user.partner_company.company_name if user.partner_company else None,
#                     "end_client": user.end_client_id,
#                     "end_client_name": user.end_client.name if user.end_client else None,
#                     "active_subscription": company_active_subscription if is_company_admin else None,
#                     "expiry_date": company_expiry_date if is_company_admin else None,
#                     "days_to_expire": company_days_to_expire if is_company_admin else None,
#                     "role": group_data,
#                     "company_role": company_role,
#                     "permission": permission_data,
#                     "group_permission": group_permission_data,
#                     "keep_me_logged_in": keep_me_logged,
#                     "last_login": user.last_login,
#                 }
#             }
#         )
#         if keep_me_logged:
#             access_token = AccessToken(token["access"])
#             refresh_token = RefreshToken(token["refresh"])

#             # Set custom lifetime
#             access_token.set_exp(lifetime=timedelta(days=365))
#             refresh_token.set_exp(lifetime=timedelta(days=365))

#             token["access"] = str(access_token)
#             token["refresh"] = str(refresh_token)

#         user.keep_me_logged_in = keep_me_logged
#         user.last_login = now()
#         user.save()

#         data = {
#             "success": True,
#             "message": "Login Successful",
#             "data": token,
#         }

#         return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make original username field (email) optional and add a common `username` field
        if "email" in self.fields:
            self.fields["email"].required = False
        self.fields["username"] = serializers.CharField(required=False)

    def validate(self, attrs):
        # login_value = attrs.get("email").lower()

        # Accept a single common field `login` (email or mobile/phone)
        request_data = self.context["request"].data
        raw_login = request_data.get("username") or attrs.get("username") or attrs.get("email")

        if not raw_login:
            raise AuthenticationFailed({"success": False, "message": "Username and password are required"})

        login_value = str(raw_login).strip()

        keep_me_logged = self.context["request"].data.get("keep_me_logged_in", False)

        # Check if the provided input contains "@" (likely an email)
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
            # Assuming phone is unique, if not, adjust the query accordingly
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

        # Check if user is active
        if not user.is_active:
            raise AuthenticationFailed(
                {
                    "success": False,
                    "message": "User account is not active. Please contact administrator.",
                }
            )

        if user.company_id:
            company = user.company
            if not company or not company.is_active:
                raise AuthenticationFailed(
                    {
                        "success": False,
                        "message": "The associated company is not active. Login is not allowed.",
                    }
                )

            # Check if company_expiry_date is expired
            company_details = (
                Company.objects.filter(id=user.company_id)
                .values("active_subscription", "expiry_date", "days_to_expire")
                .first()
                or {}
            )
            company_expiry_date = company_details.get("expiry_date")
            if company_expiry_date and company_expiry_date < timezone.now().date():
                # Get all users associated with this company
                company_users = User.objects.filter(company_id=user.company_id)

                # Get employee IDs from users who have employee relationship
                company_employee_ids = company_users.filter(employee_id__isnull=False).values_list(
                    "employee_id", flat=True
                )

                # Deactivate employees
                Employee.objects.filter(id__in=company_employee_ids).update(status="inactive")

                # Deactivate only employee users, NOT company admin users
                User.objects.filter(employee_id__in=company_employee_ids).update(is_active=False, status="inactive")

        elif user.partner_company_id:
            partner_company = user.partner_company
            if not partner_company or not partner_company.is_active:
                raise AuthenticationFailed(
                    {
                        "success": False,
                        "message": "The associated partner company is not active. Login is not allowed.",
                    }
                )
        elif user.employee_id:
            employee = user.employee
            if (
                not employee
                or not employee.company
                or not employee.company.is_active
                or not employee.partner_company.is_active
            ):
                raise AuthenticationFailed(
                    {
                        "success": False,
                        "message": "The associated employee's company is not active. Login is not allowed.",
                    }
                )

            # Check if employee is active
            if employee.status == "inactive":
                raise AuthenticationFailed(
                    {
                        "success": False,
                        "message": "Employee account is inactive. Please contact administrator.",
                    }
                )

        attrs["email"] = user.email
        try:
            token = super(CustomTokenObtainPairSerializer, self).validate(attrs)
        except AuthenticationFailed as e:
            # Check if this is a password authentication failure
            error_detail = str(e.detail).lower()
            if (
                "authentication failed" in error_detail
                or "invalid password" in error_detail
                or "no active account found" in error_detail
                or "invalid credentials" in error_detail
            ):
                # Since we already found the user, this must be a password error
                raise AuthenticationFailed(
                    {
                        "success": False,
                        "message": "Password is incorrect",
                    }
                )
            else:
                # Re-raise the original exception for other cases
                raise e

        permission_data = get_user_permissions(user)
        group_permission_data = get_user_group_permissions(user)
        group_data = get_user_groups(user)

        company_role = None
        company_expiry_date = None
        company_active_subscription = None
        company_days_to_expire = None

        # Check if user is Company Admin
        is_company_admin = any(group.get("name") == "Company Admin" for group in group_data)

        if user.company_id and is_company_admin:
            company_role = Group.objects.get(name="Company Admin").name

            # Get fresh company details after potential updates
            company_details = (
                Company.objects.filter(id=user.company_id)
                .values("active_subscription", "expiry_date", "days_to_expire")
                .first()
                or {}
            )

            company_active_subscription = company_details.get("active_subscription", None)
            company_expiry_date = company_details.get("expiry_date", None)
            company_days_to_expire = company_details.get("days_to_expire", None)

        token.update(
            {
                "userData": {
                    "user_id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "company": user.company_id if is_company_admin else None,
                    "company_name": user.company.name if (user.company and is_company_admin) else None,
                    "partner_company": user.partner_company_id,
                    "partner_company_name": user.partner_company.company_name if user.partner_company else None,
                    "end_client": user.end_client_id,
                    "end_client_name": user.end_client.name if user.end_client else None,
                    "active_subscription": company_active_subscription if is_company_admin else None,
                    "expiry_date": company_expiry_date if is_company_admin else None,
                    "days_to_expire": company_days_to_expire if is_company_admin else None,
                    "role": group_data,
                    "company_role": company_role,
                    "permission": permission_data,
                    "group_permission": group_permission_data,
                    "keep_me_logged_in": keep_me_logged,
                    "last_login": user.last_login,
                }
            }
        )

        if keep_me_logged:
            access_token = AccessToken(token["access"])
            refresh_token = RefreshToken(token["refresh"])

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
