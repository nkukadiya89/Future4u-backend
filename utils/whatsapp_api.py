import random

import requests
from decouple import config
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from user.models import User


class SendOTPViewSet(ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request):
        api_url = "https://smswaapi.in/api/send?"
        number = request.data["phone_number"]
        otp = str(random.randint(1000, 9999))
        message = (
            f"Dear Customer, your OTP is {otp}. "
            f"Please enter it to verify your mobile number. Your OTP will "
            f"expire in 10 minutes. Team PROCEM"
        )
        instance_id = config("INSTANCE_ID")
        access_token = config("ACCESS_TOKEN")

        user = get_object_or_404(User, phone=number)
        if user.whatsapp_verified:
            return Response(
                {
                    "success": True,
                    "message": "Otp is already verified",
                    "whatsapp_verified": user.whatsapp_verified,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        user.whatsapp_otp = otp  # type: ignore
        user.save()

        params = {
            "number": number,
            "type": "text",
            "message": message,
            "instance_id": instance_id,
            "access_token": access_token,
        }

        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            return Response(
                {
                    "success": True,
                    "message": "Otp sent successfully",
                    "whatsapp_verified": user.whatsapp_verified,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False},
            status=status.HTTP_400_BAD_REQUEST,
        )


class VerifyWhatsappOtpViewSet(ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request):
        number = request.data["phone_number"]
        otp = request.data["otp"]
        user = get_object_or_404(User, phone=number)
        if user.whatsapp_otp == otp:
            user.whatsapp_otp = None
            user.whatsapp_verified = True
            user.save()
            return Response(
                {
                    "success": True,
                    "message": "Otp verified successfully",
                    "whatsapp_verified": user.whatsapp_verified,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"success": False, "message": "Invalid OTP"},
            status=status.HTTP_400_BAD_REQUEST,
        )


def send_whatsapp_msg(phone_number, msg):
    api_url = "https://smswaapi.in/api/send?"
    message = msg
    instance_id = config("INSTANCE_ID")
    access_token = config("ACCESS_TOKEN")
    params = {
        "number": phone_number,
        "type": "text",
        "message": message,
        "instance_id": instance_id,
        "access_token": access_token,
    }
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        return "Whatsapp Message send"
