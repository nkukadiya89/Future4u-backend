import threading

import requests
from decouple import config
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from user.models import EmailPhoneVerify
from utils.generate_otp import generate_otp, send_otp_email
from utils.pagination import Pagination


class VerifiedOTPViewSet(ModelViewSet):
    queryset = EmailPhoneVerify.objects.filter(deleted=0).order_by("-id")
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination

    @action(detail=False, methods=["POST"], url_path="email-verify")
    def email_verify(self, request, *args, **kwargs):
        email = request.data.get("email")
        if email:
            try:
                EmailPhoneVerify.objects.get(email=email, email_verified=True)
                return Response(
                    {"success": True, "message": f"This {email} already Verifyed"},
                    status=status.HTTP_200_OK,
                )
            except ObjectDoesNotExist:
                pass

            email_otp = generate_otp()
            context = {"email": email, "otp": email_otp}

            try:
                email_verify = EmailPhoneVerify.objects.get(email=email)
                email_verify.email_otp = email_otp
                email_verify.email_verified = False
                email_verify.created_by = request.user
                email_verify.save()
            except EmailPhoneVerify.DoesNotExist:
                EmailPhoneVerify.objects.create(
                    email=email, email_otp=email_otp, created_by=request.user
                )

            email_thread = threading.Thread(
                target=send_otp_email,
                args=(
                    "One Time Password for Email Verify ",
                    "verify_email.html",
                    context,
                ),
            )
            email_thread.start()

            return Response(
                {"success": True, "message": f"Check {email} for the OTP and verify"},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": "Email Not Found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["POST"], url_path="email-otp-verifed")
    def email_otp_verifed(self, request, *args, **kwargs):
        email = request.data.get("email")
        email_otp = request.data.get("email_otp")

        if not email or not email_otp:
            return Response(
                {"success": False, "message": "Email and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        verify_email = EmailPhoneVerify.objects.get(email=email)

        if verify_email.email_otp == int(email_otp):
            verify_email.email_verified = True
            verify_email.save()
            return Response(
                {"success": True, "message": "Email Verify Successfully"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": f"Your OTP {email_otp} Incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["POST"], url_path="phone-number-verify")
    def phone_number_verify(self, request, *args, **kwargs):
        phone_number = request.data.get("phone_number")
        if phone_number:
            try:
                EmailPhoneVerify.objects.get(
                    phone_number=phone_number, phone_verified=True
                )
                return Response(
                    {
                        "success": True,
                        "message": f"This {phone_number} already Verifyed",
                    },
                    status=status.HTTP_200_OK,
                )
            except ObjectDoesNotExist:
                pass

            phone_number_otp = generate_otp()
            try:
                phone_verifed = EmailPhoneVerify.objects.get(phone_number=phone_number)
                phone_verifed.phone_number_otp = phone_number_otp
                phone_verifed.phone_verified = False
                phone_verifed.created_by = request.user
                phone_verifed.save()
            except EmailPhoneVerify.DoesNotExist:
                EmailPhoneVerify.objects.create(
                    phone_number=phone_number,
                    phone_number_otp=phone_number_otp,
                    created_by=request.user,
                )

            api_url = "http://kutility.org/app/smsapi/index.php?"
            contacts = request.data["phone_number"]
            sms_contacts = int(str(contacts)[2:])
            message = (
                f"procem.ai {phone_number_otp} is the verification "
                "code to log in to your account. "
                "Please DO NOT SHARE this code with anyone VANKTC"
            )
            params = {
                "key": config("SMS_API_KEY"),
                "campaign": config("CAMPAIGN"),
                "routeid": 7,
                "type": "text",
                "contacts": sms_contacts,
                "senderid": config("SENDERID"),
                "msg": message,
                "template_id": config("TEMPLATE_ID"),
                "pe_id": config("PE_ID"),
            }
            response = requests.get(api_url, params=params)
            if response.status_code == 200:
                return Response(
                    {
                        "success": True,
                        "message": "Otp sent successfully to your number",
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {"success": False},
                status=status.HTTP_400_BAD_REQUEST,
            )

        else:
            return Response(
                {"success": False, "message": "Phone Number Not Found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["POST"], url_path="phone-number-otp-verifed")
    def phone_number_otp_verifed(self, request, *args, **kwargs):
        phone_number = request.data.get("phone_number")
        phone_number_otp = request.data.get("phone_number_otp")

        if not phone_number or not phone_number_otp:
            return Response(
                {"success": False, "message": "Phone Number and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        verify_phone_number = EmailPhoneVerify.objects.get(phone_number=phone_number)

        if verify_phone_number.phone_number_otp == int(phone_number_otp):
            verify_phone_number.phone_verified = True
            verify_phone_number.save()
            return Response(
                {"success": True, "message": "Phone Number  Verify Successfully"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": f"Your OTP {phone_number_otp} Incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["POST"], url_path="resend-otp")
    def resend_otp(self, request, *args, **kwargs):
        email = request.data.get("email")
        phone_number = request.data.get("phone_number")

        if email:
            email_otp = generate_otp()
            context = {"email": email, "otp": email_otp}

            try:
                email_verify = EmailPhoneVerify.objects.get(
                    email=email, email_verified=False
                )
                email_verify.email_otp = email_otp
                email_verify.save()

                email_thread = threading.Thread(
                    target=send_otp_email,
                    args=(
                        "One Time Password for Email Verify ",
                        "verify_email.html",
                        context,
                    ),
                )
                email_thread.start()

                return Response(
                    {"success": True, "message": f"OTP Resend to {email}"},
                    status=status.HTTP_201_CREATED,
                )
            except EmailPhoneVerify.DoesNotExist:
                return Response(
                    {"success": False, "message": "Email Not Found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        elif phone_number:
            try:
                phone_number_otp = generate_otp()
                email_verify = EmailPhoneVerify.objects.get(
                    phone_number=phone_number, phone_verified=False
                )
                email_verify.phone_number_otp = phone_number_otp
                email_verify.save()

                api_url = "http://kutility.org/app/smsapi/index.php?"
                contacts = request.data["phone_number"]
                sms_contacts = int(str(contacts)[2:])
                message = (
                    f"procem.ai {phone_number_otp} is the verification code "
                    "to log in to your account. "
                    "Please DO NOT SHARE this code with anyone VANKTC"
                )
                params = {
                    "key": config("SMS_API_KEY"),
                    "campaign": config("CAMPAIGN"),
                    "routeid": 7,
                    "type": "text",
                    "contacts": sms_contacts,
                    "senderid": config("SENDERID"),
                    "msg": message,
                    "template_id": config("TEMPLATE_ID"),
                    "pe_id": config("PE_ID"),
                }
                response = requests.get(api_url, params=params)
                if response.status_code == 200:
                    return Response(
                        {
                            "success": True,
                            "message": "Otp sent successfully to your number",
                        },
                        status=status.HTTP_201_CREATED,
                    )
                return Response(
                    {"success": False},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            except EmailPhoneVerify.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "message": f"Phone Number {phone_number} Already Verifed",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            return Response(
                {"success": False, "message": "Phone or Email Not Found"},
                status=status.HTTP_404_NOT_FOUND,
            )
