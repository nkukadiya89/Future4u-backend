from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.cache import cache

from activity_log.models import ActivityLog
from user_profile.models import BusinessSetting, UserProfile
from user_profile.serializers import (
    BusinessSettingInfoSerializer,
    BusinessSettingSerializer,
    UserProfileSerializer,
    UserProfileUpsertSerializer,
)
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination
from utils.cache_keys import recommendation_key


class BusinessSettingViewSet(ModelViewSet):
    queryset = BusinessSetting.objects.all().order_by("-id")
    serializer_class = BusinessSettingInfoSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    search_fields = []

    ordering_fields = []

    def get_queryset(self):
        user = self.request.user
        queryset = BusinessSetting.objects.filter(Q(user_id=user) | Q(company=user.company)).order_by("-id")
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        data = request.data
        data["user"] = request.user.id
        data["user_id"] = request.user.id
        serializer = BusinessSettingSerializer(data=data)

        if serializer.is_valid():
            instance = serializer.save()
            response_serializer = BusinessSettingInfoSerializer(instance)
            payload = response_serializer.data

            # Tailor response when company business setting is created
            if instance.company_id:
                filtered = {
                    "id": payload.get("id"),
                    "company": payload.get("company"),
                    "company_name": payload.get("company_name"),
                    "notifications": payload.get("notifications"),
                    "sgst": payload.get("sgst"),
                    "cgst": payload.get("cgst"),
                    "igst": payload.get("igst"),
                    "country": payload.get("country"),
                    "country_name": payload.get("country_name"),
                    "state": payload.get("state"),
                    "state_name": payload.get("state_name"),
                    "city": payload.get("city"),
                    "city_name": payload.get("city_name"),
                    "currency": payload.get("currency"),
                }
                return Response({"success": True, "data": filtered}, status=status.HTTP_201_CREATED)

            return Response({"success": True, "data": payload}, status=status.HTTP_201_CREATED)
        else:
            error_messages = " ".join([", ".join(value) for value in serializer.errors.values()])
            return Response(
                {"success": False, "message": error_messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        company_id = request.query_params.get("company_id")

        try:
            if company_id:
                business_setting = BusinessSetting.objects.get(company_id=company_id)
            else:
                # Fallback to pk if neither is provided
                business_setting = BusinessSetting.objects.get(id=pk)

            serializer = self.serializer_class(business_setting)
            return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)
        except BusinessSetting.DoesNotExist:
            return Response(
                {"success": False, "message": "Business Setting does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def update(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        company_id = request.query_params.get("company_id")

        try:
            if company_id:
                business_setting = BusinessSetting.objects.get(company_id=company_id)
            else:
                # Fallback to pk if neither is provided
                business_setting = BusinessSetting.objects.get(id=pk)
        except BusinessSetting.DoesNotExist:
            return Response(
                {"success": False, "message": "Business Setting does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BusinessSettingSerializer(business_setting, data=request.data, partial=True)
        if serializer.is_valid():
            instance = serializer.save()
            response_serializer = BusinessSettingInfoSerializer(instance)
            payload = response_serializer.data
            ip_address = get_client_ip(request)
            ActivityLog.log.business_setting_update(
                business_setting=instance,
                ip_address=ip_address,
                user=request.user,
                company=instance.company,
            )

            # Tailor response when company business setting is updated
            if instance.company_id:
                filtered = {
                    "id": payload.get("id"),
                    "company": payload.get("company"),
                    "company_name": payload.get("company_name"),
                    "notifications": payload.get("notifications"),
                    "sgst": payload.get("sgst"),
                    "cgst": payload.get("cgst"),
                    "igst": payload.get("igst"),
                    "country": payload.get("country"),
                    "country_name": payload.get("country_name"),
                    "state": payload.get("state"),
                    "state_name": payload.get("state_name"),
                    "city": payload.get("city"),
                    "city_name": payload.get("city_name"),
                    "currency": payload.get("currency"),
                }
                return Response({"success": True, "data": filtered}, status=status.HTTP_200_OK)

            return Response({"success": True, "data": payload}, status=status.HTTP_200_OK)
        else:
            error_messages = " ".join([", ".join(value) for value in serializer.errors.values()])
            return Response(
                {"success": False, "message": error_messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"], url_path="business-setting-data")
    def business_setting_data(self, request, *args, **kwargs):
        try:
            business_setting = (
                self.get_queryset().select_related("country", "state", "city").filter(user_id=request.user).first()
            )

            # If no business setting found, return null data
            if not business_setting:
                return Response(
                    {
                        "success": True,
                        "data": {
                            "country_id": None,
                            "country_name": None,
                            "state_id": None,
                            "state_name": None,
                            "city_id": None,
                            "city_name": None,
                            "sgst": None,
                            "cgst": None,
                            "igst": None,
                            "currency": None,
                        },
                    }
                )
        except Exception:
            return Response(
                {
                    "success": True,
                    "data": {
                        "country_id": None,
                        "country_name": None,
                        "state_id": None,
                        "state_name": None,
                        "city_id": None,
                        "city_name": None,
                        "sgst": None,
                        "cgst": None,
                        "igst": None,
                        "currency": None,
                    },
                }
            )

        # If location data is not configured, return null for location fields
        if not all([business_setting.country, business_setting.state, business_setting.city]):
            return Response(
                {
                    "success": True,
                    "data": {
                        "country_id": business_setting.country.id if business_setting.country else None,
                        "country_name": business_setting.country.name if business_setting.country else None,
                        "state_id": business_setting.state.id if business_setting.state else None,
                        "state_name": business_setting.state.name if business_setting.state else None,
                        "city_id": business_setting.city.id if business_setting.city else None,
                        "city_name": business_setting.city.name if business_setting.city else None,
                        "sgst": business_setting.sgst,
                        "cgst": business_setting.cgst,
                        "igst": business_setting.igst,
                        "currency": business_setting.currency,
                    },
                }
            )

        return Response(
            {
                "success": True,
                "data": {
                    "country_id": business_setting.country.id if business_setting.country else None,
                    "country_name": business_setting.country.name if business_setting.country else None,
                    "state_id": business_setting.state.id if business_setting.state else None,
                    "state_name": business_setting.state.name if business_setting.state else None,
                    "city_id": business_setting.city.id if business_setting.city else None,
                    "city_name": business_setting.city.name if business_setting.city else None,
                    "sgst": business_setting.sgst,
                    "cgst": business_setting.cgst,
                    "igst": business_setting.igst,
                    "currency": business_setting.currency,
                },
            }
        )


class UserProfileViewSet(ModelViewSet):
    """
    Endpoints:
    - GET   /api/profile/
    - POST  /api/profile/
    - PATCH /api/profile/
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get", "post", "patch", "head", "options"]
    # Rate limiting (view-level, safe)
    from utils.throttles import PerUserBurstRateThrottle  # local import avoids broad dependency at module import time

    throttle_classes = [PerUserBurstRateThrottle]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user).select_related("education_level", "stream")

    def list(self, request, *args, **kwargs):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        data = UserProfileSerializer(profile).data
        return Response({"success": True, "status": True, "message": "", "data": data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        ser = UserProfileUpsertSerializer(profile, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(
                {"success": False, "status": False, "message": ser.errors, "data": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser.save()
        try:
            cache.delete(recommendation_key(request.user.id))
        except Exception:
            pass
        out = UserProfileSerializer(profile).data
        return Response(
            {"success": True, "status": True, "message": "Profile saved", "data": out},
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        ser = UserProfileUpsertSerializer(profile, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(
                {"success": False, "status": False, "message": ser.errors, "data": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser.save()
        try:
            cache.delete(recommendation_key(request.user.id))
        except Exception:
            pass
        out = UserProfileSerializer(profile).data
        return Response(
            {"success": True, "status": True, "message": "Profile updated", "data": out},
            status=status.HTTP_200_OK,
        )
