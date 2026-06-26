from datetime import timedelta
import json

from utils.auth import is_web_source, validate_password_strength
from django.contrib.auth import logout
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from user.models import User
from email_utils.send_email import generate_token, send_mail, decode_token
from user.services.registration_service import (
    send_registration_email,
    send_verify_email,
)
from user.user_type_serializers import RegisterSerializer


class AuthViewSet(viewsets.ViewSet):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @action(
        detail=False,
        methods=["post"],
        url_path="register",
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def register(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            user = serializer.save()

            try:
                json_data = json.loads(request.data.get("data", "{}"))
                source = json_data.get("source")
            except (json.JSONDecodeError, TypeError, AttributeError):
                source = None

            if not user.is_active and not is_web_source(source):
                send_registration_email(user)

            response_data = {
                "success": True,
                "user_id": user.id,
                "user_type": user.user_type,
            }
            if is_web_source(source):
                response_data.update(
                    {
                        "message": (
                            "Registration successful. "
                            "A password setup link has been sent to your email."
                        ),
                        "must_change_password": True,
                    }
                )
            else:
                response_data["message"] = (
                    "Registration successful. Please verify your email with the OTP sent."
                )

            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        authentication_classes=[],
        url_path="verify-success",
    )
    def verify_success(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response(
                {"success": False, "error": "Email and OTP are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"success": False, "error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not user.otp_created_at or timezone.now() - user.otp_created_at > timedelta(
            days=1
        ):
            return Response(
                {
                    "success": False,
                    "error": "OTP has expired. Please request a new one.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.otp != int(otp):
            return Response(
                {"success": False, "error": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.status = "active"
        user.email_verified = True
        user.otp = None
        user.otp_created_at = None
        user.save(
            update_fields = [
                "is_active",
                "status",
                "email_verified",
                "otp",
                "otp_created_at",
            ]
        )
        return Response(
            {"success": True, "message": "Your email has been verified, and your account has been created successfully"},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="resend-otp",
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def resend_otp(self, request):
        email = request.data.get("email")

        if not email:
            return Response(
                {"success": False, "error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"success": False, "error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_active:
            return Response(
                {"success": False, "error": "Email is already verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = send_verify_email(user.email, user.first_name)
        user.otp = otp
        user.otp_created_at = timezone.now()
        user.save(update_fields=["otp", "otp_created_at"])

        return Response(
            {
                "success": True,
                "message": "OTP resent successfully. Please check your email.",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False,methods=["post"],url_path="logout",
        permission_classes=[IsAuthenticated],
        authentication_classes=[JWTAuthentication],
    )
    def logout(self, request):
        try:
            logout(request)
            return Response(
                {"success": True, "message": "Logout successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"success": False, "message": "Logout failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False,methods=["post"],url_path="change-password",
        permission_classes=[IsAuthenticated],
        authentication_classes=[JWTAuthentication],
    )
    def change_password(self, request):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not current_password:
            return Response(
                {"success": False, "error": "Current password is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not new_password:
            return Response(
                {"success": False, "error": "New password is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if confirm_password is not None and new_password != confirm_password:
            return Response(
                {"success": False, "error": "Passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password_errors = validate_password_strength(new_password)
        if password_errors:
            return Response(
                {"success": False, "errors": password_errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(current_password):
            return Response(
                {"success": False, "error": "Current password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.must_change_password = False
        user.password_last_changed = timezone.now()
        user.save(
            update_fields=[
                "password",
                "must_change_password",
                "password_last_changed",
            ]
        )

        return Response(
            {"success": True, "message": "Password changed successfully"},
            status=status.HTTP_200_OK,
        )

    # forget password flow
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        authentication_classes=[],
        url_path="forgot-password",
    )
    def forgot_password(self, request):
        email = request.data.get("email")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"success": False, "error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.is_active:
            return Response(
                {"success": False, "error": "User not active"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token = generate_token(user.email, 1)
        send_mail("Password Reset Request", "reset-pass.html", {"token": token, "name": user.first_name, "email": user.email})  # type: ignore

        return Response(
            {
                "success": True,
                "message": "Password reset instructions sent to your email",
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="reset-password",
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def reset_password(self, request):
        token = request.data.get("token")
        new_password = request.data.get("new_password")
        re_enter_password = request.data.get("re_enter_password")

        if not token:
            return Response(
                {"success": False, "error": "Token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not new_password or not re_enter_password:
            return Response(
                {
                    "success": False,
                    "error": "new_password and re_enter_password are required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != re_enter_password:
            return Response(
                {"success": False, "error": "Passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password_errors = validate_password_strength(new_password)
        if password_errors:
            return Response(
                {"success": False, "errors": password_errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = decode_token(token)
        except Exception:
            return Response(
                {"success": False, "error": "Invalid or expired token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email = payload.get("email")
        if not email:
            return Response(
                {"success": False, "error": "Invalid token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user = User.objects.get(email=email) 
        except User.DoesNotExist:
            return Response(
                {"success": False, "error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        was_pending = not user.is_active or user.status == "pending"
        user.set_password(new_password)
        user.must_change_password = False
        user.password_last_changed = timezone.now()
        update_fields = [
            "password",
            "must_change_password",
            "password_last_changed",
        ]
        if was_pending:
            user.is_active = True
            user.status = "active"
            user.email_verified = True
            update_fields.extend(["is_active", "status", "email_verified"])

        user.save(update_fields=update_fields)
        message = (
            "Password set successfully."
            if was_pending
            else "Password reset successfully"
        )
        return Response(
            {"success": True, "message": message},
            status=status.HTTP_200_OK,
        )