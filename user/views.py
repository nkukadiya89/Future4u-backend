import json
import random
import threading

from django.utils import timezone

from django.contrib.auth import logout
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from company.models import Company
from email_utils.send_email import decode_token, generate_forget_pass_token, send_mail
from email_utils.send_success_mail import send_confirm_mail, send_success_mail
from employee.models import Employee
from user.models import RoleFamily, User
from user.serializers import (
    LoginWithEmailOtpSerializer,
    RoleFamilySerializer,
    UserDetailsSerializer,
    VerifyLoginWithEmailOtpSerializer,
    VerifyOTPSerializer,
)
from user.user_auth import (
    get_user_group_permissions,
    get_user_groups,
    get_user_permissions,
)
from utils.generate_otp import generate_otp, send_otp_email
from utils.pagination import Pagination


class UserDetailsViewSet(ModelViewSet):
    queryset = User.objects.all().order_by("-id")
    serializer_class = UserDetailsSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def list(self, request, *args, **kwargs):
        serializer = self.serializer_class(request.user)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "message": "User details updated", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class VerifyOtpViewSet(ModelViewSet):
    serializer_class = VerifyOTPSerializer
    queryset = User.objects.all().order_by("-id")

    @transaction.atomic
    def create(self, request, **kwargs):
        data = request.data
        serializer = self.get_serializer(data=data, partial=True)
        if serializer.is_valid():
            email = data.get("email")
            otp = data.get("otp")
            user = User.objects.filter(email=email).first()
            if user is None:
                return Response(
                    {"success": False, "message": "User not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if user.otp == otp:
                user.is_active = True
                user.status = "active"
                user.otp = None
                user.save()
                return Response(
                    {
                        "success": True,
                        "message": "OTP verification successful. You are registered.",
                    }
                )
            else:
                return Response(
                    {"success": False, "message": "Invalid OTP"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgetPasswordViewSet(ModelViewSet):
    queryset = User.objects.all().order_by("-id")
    serializer_class = VerifyOTPSerializer
    permission_classes = [AllowAny]

    # @transaction.atomic
    def create(self, request, *args, **kwargs):
        email = request.data.get("email")

        if not email:
            return Response(
                {"success": False, "message": "Email not Found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {"success": False, "message": "User not Found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if not user.is_active:
                return Response(
                    {"success": False, "message": "User not active with us"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            user_phone = user.phone
            token = generate_forget_pass_token(email, user_phone, 30)
            name = user.first_name

            # Email Context
            context = {"name": name, "token": token, "email": email}
            current_site = request._current_scheme_host + request.path
            context["current_site"] = current_site
            send_mail("Forgot Your Password", "forgot-pass.html", context)
            return Response(
                {
                    "success": True,
                    "message": "Forgot Password Link has been sent to "
                    "Registed Phone Number and Email",
                },
                status=status.HTTP_200_OK,
            )


class ResetPasswordViewSet(ModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]
    queryset = User.objects.all().order_by("-id")

    def create(self, request, token, *args, **kwargs):
        with transaction.atomic():
            try:
                res_data = json.loads(request.body.decode("utf-8"))
            except Exception:
                return Response(
                    {"success": False, "message": "Service not available"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            try:
                payload = decode_token(token)
            except Exception:
                return Response(
                    {"success": False, "message": "Token Expired"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if "email" not in payload:
                return Response(
                    {"success": False, "message": "Invalid Token"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            user = User.objects.filter(email=payload["email"]).first()
            if user is None:
                return Response(
                    {"success": False, "message": "Email is not registered"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            password1 = res_data.get("password1", None)
            password2 = res_data.get("password2", None)
            if password1 is None or password2 is None:
                return Response(
                    {"success": False, "message": "Provide valid Password"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if password1 != password2:
                return Response(
                    {"success": False, "message": "Passwords do not match."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            employee = Employee.objects.filter(user=user).first()
            if employee:
                employee.status = "active"
                employee.save()

            company = Company.objects.filter(user=user).first()
            if company:
                company.status = "active"
                company.is_active = True
                company.save()

            user.set_password(password1)
            user.is_active = True
            user.password_last_changed = timezone.now()
            user.status = "active"
            user.save()

        if user.last_login is None:
            context = {
                "name": user.first_name,
                "email": user.email,
            }

            send_success_mail(
                "Registration successful",
                "register-success.html",
                context,
            )
            return Response(
                {"success": True, "message": "Password changed successfully"},
                status=status.HTTP_200_OK,
            )

        else:
            context = {"name": user.first_name, "email": user.email}
            send_confirm_mail(
                "OutdoorX Password Change Notification",
                "password-changed-confirmation.html",
                context,
            )
            return Response(
                {"success": True, "message": "Password changed successfully"},
                status=status.HTTP_200_OK,
            )


class ForgotPasswordViewSet(ModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]
    queryset = User.objects.all().order_by("-id")

    def create(self, request, token, *args, **kwargs):
        with transaction.atomic():
            try:
                res_data = json.loads(request.body.decode("utf-8"))
            except Exception:
                return Response(
                    {"success": False, "message": "Service not available"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            try:
                payload = decode_token(token)
            except Exception:
                return Response(
                    {"success": False, "message": "Token Expired"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if "email" not in payload:
                return Response(
                    {"success": False, "message": "Invalid Token"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            user = User.objects.filter(email=payload["email"]).first()
            if user is None:
                return Response(
                    {"success": False, "message": "Email is not registered"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            new_password = res_data.get("new_password")
            re_enter_password = res_data.get("re_enter_password")

            if not (new_password and re_enter_password):
                return Response(
                    {
                        "success": False,
                        "message": "Both new_password and re_enter_password are required.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if new_password != re_enter_password:
                return Response(
                    {
                        "success": False,
                        "message": "New password and Re-enter password do not match.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            employee = Employee.objects.filter(user=user).first()
            if employee:
                employee.status = "active"
                employee.save()

            company = Company.objects.filter(user=user).first()
            if company:
                company.status = "active"
                company.is_active = True
                company.save()

            user.set_password(new_password)
            user.is_active = True
            user.password_last_changed = timezone.now()
            user.status = "active"
            user.save()

        if user.last_login is None:
            context = {
                "name": user.first_name,
                "email": user.email,
            }

            send_success_mail(
                "Registration successful",
                "register-success.html",
                context,
            )
            return Response(
                {"success": True, "message": "Password changed successfully"},
                status=status.HTTP_200_OK,
            )


class LoginWithEmailOtpViewset(ModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]
    serializer_class = LoginWithEmailOtpSerializer
    queryset = User.objects.all().order_by("-id")

    def create(self, request, *args, **kwargs):
        data = request.data
        otp_method = data["otp_method"]
        phone = data["phone"]

        if otp_method == "email":
            user_email = User.objects.filter(email=data["email"]).first()

            if not user_email:
                return Response(
                    {"success": False, "message": "Email is not registered with us!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = self.serializer_class(data=data)
            if serializer.is_valid():
                otp = generate_otp()
                context = {
                    "email": user_email.email,
                    "name": user_email.first_name,
                    "otp": otp,
                }
                user_email.otp = otp
                user_email.save()

                email_thread = threading.Thread(
                    target=send_otp_email,
                    args=("Your One Time Password", "account-otp.html", context),
                )
                email_thread.start()

                return Response(
                    {"success": True, "message": "Check your email for the OTP."},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        elif otp_method == "phone":
            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                return Response(
                    {"success": False, "message": "Phone number not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except MultipleObjectsReturned:
                return Response(
                    {
                        "success": False,
                        "message": "Multiple users found with this phone number.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # WhatsApp verification logic removed - field no longer exists
            # TODO: Implement alternative phone verification method
            return Response(
                {
                    "success": False,
                    "message": "WhatsApp verification temporarily disabled",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        else:
            return Response(
                {"success": False, "message": "Provide Email or Phone Number"},
                status=status.HTTP_404_NOT_FOUND,
            )


class VerifyEmailOtpAndGiveTokenViewset(ModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]
    serializer_class = VerifyLoginWithEmailOtpSerializer
    queryset = User.objects.all().order_by("-id")

    def create(self, request, *args, **kwargs):
        data = request.data
        email = data["email"]
        phone = data["phone"]
        user = None

        if email or phone:
            serializer = self.serializer_class(data=data)
            if serializer.is_valid():
                otp = int(serializer.validated_data["otp"])

                try:
                    if email:
                        user = User.objects.get(email=email)
                    elif phone:
                        user = User.objects.get(phone=phone)
                except User.DoesNotExist:
                    return Response(
                        {
                            "success": False,
                            "message": "User with this email/phone does not exist.",
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )

                if user.otp == otp:
                    user.otp = None
                    user.is_active = True
                    user.save()

                    refresh = RefreshToken.for_user(user)
                    access_token = str(refresh.access_token)

                    company_profile_perc = 0
                    company_profile_count = None
                    # Company subscription logic removed - users are now standalone
                    company_active_subscription = None
                    # TODO: Implement alternative subscription management

                    # Fetching permissions and groups
                    permission_data = get_user_permissions(user)
                    group_permission_data = get_user_group_permissions(user)
                    group_data = get_user_groups(user)

                    # Company info logic removed - users are now standalone
                    company_id = None
                    # TODO: Implement alternative user identification

                    user_data = {
                        "user_id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "phone": user.phone,
                        "company": company_id,
                        "active_subscription": company_active_subscription,
                        "user_type": user.user_type,
                        "permission": permission_data,
                        "group_permission": group_permission_data,
                        "company_profile_count": company_profile_count,
                        "company_profile_perc": company_profile_perc,
                    }

                    data = {
                        "success": True,
                        "message": "Login Successful",
                        "data": {
                            "refresh": str(refresh),
                            "access": access_token,
                            "userData": user_data,
                        },
                    }

                    return Response(data, status=status.HTTP_200_OK)

                else:
                    return Response(
                        {"success": False, "message": "Incorrect OTP."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"success": False, "message": "Email or phone is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LogoutViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            logout(request)

            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"error": "Logout failed"}, status=status.HTTP_400_BAD_REQUEST
            )


class RoleFamilyViewSet(ModelViewSet):
    queryset = RoleFamily.objects.filter(deleted=False).order_by("-id")
    serializer_class = RoleFamilySerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")

        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        else:
            if no_pagination:
                serializer = self.serializer_class(queryset, many=True)
                return Response({"success": True, "data": serializer.data})
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.serializer_class(page, many=True)
                return self.get_paginated_response(
                    {"success": True, "data": serializer.data}
                )

            serializer = self.serializer_class(queryset, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

    def create(self, request, *args, **kwargs):
        data = request.data
        data["created_by"] = request.user.id
        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        else:
            error_message = " ".join(
                [", ".join(value) for value in serializer.errors.values()]
            )
            return Response(
                {"success": False, "message": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data
        data["updated_by"] = request.user.id
        serializer = self.serializer_class(instance, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )

        else:
            error_message = " ".join(
                [", ".join(value) for value in serializer.errors.values()]
            )
            return Response(
                {"success": True, "data": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.save()
        return Response(
            {"success": True, "message": "Role Family Deleted SuccessFully."},
            status=status.HTTP_200_OK,
        )
