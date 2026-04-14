import threading

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from email_utils.send_email import generate_forget_pass_token, send_mail

User = get_user_model()


class ResendPasswordResetViewSet(ModelViewSet):
    """
    Resend password reset email for any user type (Company, Partner Company, End Client, Employee)
    """

    queryset = User.objects.all().order_by("-id")
    permission_classes = [AllowAny]

    def send_email_thread(self, context):
        """Send email in background thread"""
        send_mail(
            "Future4U Security Alert For Reset Your Password",
            "reset-pass.html",
            context,
        )

    def create(self, request, *args, **kwargs):
        """
        Resend password reset email
        Request body: {"email": "user@example.com"}
        """
        email = request.data.get("email")

        if not email:
            return Response(
                {"success": False, "message": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {"success": False, "message": "User not found with this email"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if not user.is_active:
                return Response(
                    {"success": False, "message": "User account is not active"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get user details based on user type
            user_name = user.first_name
            user_phone = user.phone

            # Generate new token
            token = generate_forget_pass_token(email, user_phone, 30)

            # Prepare email context
            context = {
                "name": user_name,
                "token": token,
                "email": email,
            }

            # Send email in background thread
            email_thread = threading.Thread(
                target=self.send_email_thread,
                args=(context,),
            )
            email_thread.start()

            return Response(
                {
                    "success": True,
                    "message": "Password reset email has been resent successfully",
                    # "data": {"email": email, "user_type": self._get_user_type(user)},
                },
                status=status.HTTP_200_OK,
            )

    def _get_user_type(self, user):
        """Determine the user type"""
        from company.models import Company
        from employee.models import Employee

        if Company.objects.filter(user=user).exists():
            return "Company"
        elif Employee.objects.filter(user=user).exists():
            return "Employee"
        else:
            return "User"
