from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from user.models import User
from email_utils.send_email import generate_token, send_mail
from user.services.registration_service import send_registration_email
from user.user_type_serializers import RegisterSerializer


class AuthViewSet(viewsets.ViewSet):

    @action(
        detail=False,
        methods=["post"],
        url_path="register",
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)

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
        if user.otp != int(otp):  # type: ignore
            return Response(
                {"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = True
        user.otp = None  # type: ignore
        user.save()  # type: ignore
        return Response(
            {"message": "Email verified successfully"}, status=status.HTTP_200_OK
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

        # Generate a password reset token and send it via email
        # token valid for 1 day
        token = generate_token(user.email, 1)
        send_mail("Password Reset Request", "reset-pass.html", {"token": token, "name": user.first_name, "email": user.email})  # type: ignore

        return Response(
            {"message": "Password reset instructions sent to your email"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="reset-password/")
    def reset_password(self, request):
        email = request.data.get("email")
        new_password = request.data.get("new_password")

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
