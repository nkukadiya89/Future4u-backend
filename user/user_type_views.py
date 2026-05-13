from django.utils import timezone
from datetime import timedelta
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from user.models import User
from email_utils.send_email import generate_token, send_mail, decode_token
from user.services.registration_service import send_registration_email, send_verify_email
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
            send_registration_email(user)

            return Response(
                {
                    "message": "User registered successfully",
                    "user_id": user.id,  # type: ignore
                    "user_type": user.user_type,  # type: ignore
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                {"error": "Email and OTP are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)  # type: ignore
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        # Check OTP expiry first (1 day)
        if not user.otp_created_at or timezone.now() - user.otp_created_at > timedelta(days=1):
            return Response(
                {"error": "OTP has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.otp != int(otp):
            return Response(
                {"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = True
        user.otp = None
        user.otp_created_at = None
        user.save()
        return Response(
            {"message": "Email verified successfully"}, status=status.HTTP_200_OK
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
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_active:
            return Response(
                {"error": "Email is already verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = send_verify_email(user.email, user.first_name)
        user.otp = otp
        user.otp_created_at = timezone.now()
        user.save(update_fields=["otp", "otp_created_at"])

        return Response(
            {"message": "OTP resent successfully. Please check your email."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not user.check_password(current_password):
            return Response(
                {"error": "Current password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        return Response(
            {"message": "Password changed successfully"}, status=status.HTTP_200_OK
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
            user = User.objects.get(email=email)  # type: ignore
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if user is active
        if not user.is_active:
            return Response(
                {"error": "User not active"}, status=status.HTTP_401_UNAUTHORIZED
            )

        token = generate_token(user.email, 1)
        send_mail("Password Reset Request", "reset-pass.html", {"token": token, "name": user.first_name, "email": user.email})  # type: ignore

        return Response(
            {"message": "Password reset instructions sent to your email"},
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
                {"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not new_password or not re_enter_password:
            return Response(
                {"error": "new_password and re_enter_password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != re_enter_password:
            return Response(
                {"error": "Passwords do not match"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payload = decode_token(token)
        except Exception:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email = payload.get("email")
        if not email:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            user = User.objects.get(email=email)  # type: ignore
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user.set_password(new_password)
        user.save()
        return Response(
            {"message": "Password reset successfully"}, status=status.HTTP_200_OK
        )
