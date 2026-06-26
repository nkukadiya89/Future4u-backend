import json

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.cache import cache
from utils.throttles import (PerUserBurstRateThrottle)  

from activity_log.models import ActivityLog
from common.mixins.view_mixins import ListEnvelopeMixin
from user_profile.models import (
    BusinessSetting,
    ChildProfile,
    CorporateGallery,
    CorporateProfile,
    ParentProfile,
    ProfessionalProfile,
    SchoolCollegeGallery,
    SchoolCollegeProfile,
    StudentProfile,
    UserProfile,
    InstituteProfile,
    InstituteGallery,
)
from user_profile.organization_viewsets import (
    OrganizationGalleryViewSet,
    OrganizationProfileViewSet,
)
from user_profile.serializers import (
    BusinessSettingInfoSerializer,
    BusinessSettingSerializer,
    ChildProfileCreateSerializer,
    ChildProfileSerializer,
    ParentProfileSerializer,
    ParentProfileUpsertSerializer,
    ProfessionalProfileSerializer,
    ProfessionalProfileUpsertSerializer,
    StudentProfileSerializer,
    StudentProfileUpsertSerializer,
    UserProfileSerializer,
    UserProfileUpsertSerializer,
    InstituteProfileUpSerializer,
    InstituteProfileSerializer,
    InstituteGallerySerializer,
    SchoolCollegeProfileSerializer,
    SchoolCollegeProfileUpSerializer,
    SchoolCollegeGallerySerializer,
    CorporateProfileSerializer,
    CorporateProfileUpSerializer,
    CorporateGallerySerializer,
)
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination
from utils.cache_keys import recommendation_key
from utils.throttles import PerUserBurstRateThrottle


class ChildProfileViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return ChildProfile.objects.filter(
            parent_profile__user=self.request.user,
            deleted=False,
        ).select_related("education_level", "stream").prefetch_related("language")

    def get_serializer_class(self):
        if self.action in ("create", "partial_update", "update"):
            return ChildProfileCreateSerializer
        return ChildProfileSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.get("data")
        if data:
            data = json.loads(data)
        else:
            data = request.data

        first_name = data.get("first_name")
        last_name = data.get("last_name")
        date_of_birth = data.get("date_of_birth")

        if first_name and last_name and date_of_birth:
            exists = ChildProfile.objects.filter(
                parent_profile__user=request.user,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                deleted=False,
            ).exists()
            if exists:
                return Response(
                    {
                        "success": False,
                        "message": "A child with the same name and date of birth already exists under your profile.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        parent_profile = ParentProfile.objects.filter(user=request.user).first()
        if not parent_profile:
            return Response(
                {"success": False, "message": "Parent profile not found. Please set up your profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        child = serializer.save(parent_profile=parent_profile)

        profile_image_file = request.FILES.get("profile_image")
        if profile_image_file:
            try:
                child.upload_profile_image(profile_image_file)
            except Exception as e:
                return Response(
                    {"success": False, "message": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {
                "success": True,
                "message": "Child profile created",
                "data": ChildProfileSerializer(child).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        child = self.get_object()
        data = request.data.get("data")
        if data:
            data = json.loads(data)
        else:
            data = {}
        serializer = self.get_serializer(child, data=data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        child = serializer.save()

        profile_image_file = request.FILES.get("profile_image")
        if profile_image_file:
            try:
                child.upload_profile_image(profile_image_file)
            except Exception as e:
                return Response(
                    {"success": False, "message": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {
                "success": True,
                "message": "Child profile updated",
                "data": ChildProfileSerializer(child).data,
            },
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        child = self.get_object()
        serializer = self.get_serializer(child)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        child = self.get_object()
        child.deleted = True
        child.deleted_at = timezone.now()
        child.save(update_fields=["deleted", "deleted_at"])
        return Response(
            {"success": True, "message": "Child removed"},
            status=status.HTTP_200_OK,
        )


class BusinessSettingViewSet(ListEnvelopeMixin, ModelViewSet):
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
        queryset = BusinessSetting.objects.filter(
            Q(user_id=user) | Q(company=user.company)
        ).order_by("-id")
        return queryset

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
                return Response(
                    {"success": True, "data": filtered}, status=status.HTTP_201_CREATED
                )

            return Response(
                {"success": True, "data": payload}, status=status.HTTP_201_CREATED
            )
        else:
            error_messages = " ".join(
                [", ".join(value) for value in serializer.errors.values()]
            )
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
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
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

        serializer = BusinessSettingSerializer(
            business_setting, data=request.data, partial=True
        )
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
                return Response(
                    {"success": True, "data": filtered}, status=status.HTTP_200_OK
                )

            return Response(
                {"success": True, "data": payload}, status=status.HTTP_200_OK
            )
        else:
            error_messages = " ".join(
                [", ".join(value) for value in serializer.errors.values()]
            )
            return Response(
                {"success": False, "message": error_messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"], url_path="business-setting-data")
    def business_setting_data(self, request, *args, **kwargs):
        try:
            business_setting = (
                self.get_queryset()
                .select_related("country", "state", "city")
                .filter(user_id=request.user)
                .first()
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
        if not all(
            [business_setting.country, business_setting.state, business_setting.city]
        ):
            return Response(
                {
                    "success": True,
                    "data": {
                        "country_id": (
                            business_setting.country.id
                            if business_setting.country
                            else None
                        ),
                        "country_name": (
                            business_setting.country.name
                            if business_setting.country
                            else None
                        ),
                        "state_id": (
                            business_setting.state.id
                            if business_setting.state
                            else None
                        ),
                        "state_name": (
                            business_setting.state.name
                            if business_setting.state
                            else None
                        ),
                        "city_id": (
                            business_setting.city.id if business_setting.city else None
                        ),
                        "city_name": (
                            business_setting.city.name
                            if business_setting.city
                            else None
                        ),
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
                    "country_id": (
                        business_setting.country.id
                        if business_setting.country
                        else None
                    ),
                    "country_name": (
                        business_setting.country.name
                        if business_setting.country
                        else None
                    ),
                    "state_id": (
                        business_setting.state.id if business_setting.state else None
                    ),
                    "state_name": (
                        business_setting.state.name if business_setting.state else None
                    ),
                    "city_id": (
                        business_setting.city.id if business_setting.city else None
                    ),
                    "city_name": (
                        business_setting.city.name if business_setting.city else None
                    ),
                    "sgst": business_setting.sgst,
                    "cgst": business_setting.cgst,
                    "igst": business_setting.igst,
                    "currency": business_setting.currency,
                },
            }
        )


class UserProfileViewSet(ModelViewSet):
    """
    Base profile endpoint ONLY for Super Admin
    Endpoints:
    - GET   /api/profile/
    - PATCH /api/profile/
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get", "patch", "head", "options"]

    throttle_classes = [PerUserBurstRateThrottle]

    def get_queryset(self):
        # Only Super Admin can access UserProfile
        if self.request.user.user_type != self.request.user.Role.SUPER_ADMIN:
            return UserProfile.objects.none()
        return UserProfile.objects.filter(user=self.request.user).select_related("user")

    def list(self, request, *args, **kwargs):
        if request.user.user_type != request.user.Role.SUPER_ADMIN:
            return Response(
                {
                    "success": False,
                    "message": "Only Super Admin can access this endpoint",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        profile = UserProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(
                {"success": False, "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = UserProfileSerializer(profile).data
        return Response(
            {"success": True, "data": data},
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        # Only Super Admin can access UserProfile
        if request.user.user_type != request.user.Role.SUPER_ADMIN:
            return Response(
                {
                    "success": False,
                    "message": "Only Super Admin can access this endpoint",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        profile = UserProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(
                {"success": False, "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = UserProfileUpsertSerializer(profile, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser.save()
        try:
            cache.delete(recommendation_key(request.user.id))
        except Exception:
            pass
        out = UserProfileSerializer(profile).data
        return Response(
            {
                "success": True,
                "message": "Profile updated",
                "data": out,
            },
            status=status.HTTP_200_OK,
        )


class StudentProfileViewSet(ModelViewSet):
    """
    Student-specific profile endpoint
    Endpoints:
    - GET   /api/student-profile/
    - PATCH /api/student-profile/
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get", "patch", "head", "options"]

    throttle_classes = [PerUserBurstRateThrottle]

    def get_queryset(self):
        return StudentProfile.objects.filter(user=self.request.user).select_related(
            "user__country", "user__states", "user__city", "education_level", "stream"
        )

    def list(self, request, *args, **kwargs):
        profile = StudentProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(
                {"success": False, "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = StudentProfileSerializer(profile).data
        return Response(
            {"success": True, "data": data},
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        profile = StudentProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(
                {"success": False, "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data.get("data")
        if data:
            data = json.loads(data)
        else:
            data = {}

        profile_image = request.FILES.get("profile_image")
        if profile_image:
            request.user.upload_profile_image(profile_image)

        serializer = StudentProfileUpsertSerializer(profile, data=data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        try:
            cache.delete(recommendation_key(request.user.id))
        except Exception:
            pass
        out = StudentProfileSerializer(profile).data
        return Response(
            {
                "success": True,
                "message": "Student profile updated",
                "data": out,
            },
            status=status.HTTP_200_OK,
        )


class ProfessionalProfileViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get", "patch", "head", "options"]

    throttle_classes = [PerUserBurstRateThrottle]

    def get_queryset(self):
        return ProfessionalProfile.objects.filter(
            user=self.request.user
        ).select_related(
            "user__country", "user__states", "user__city", "education_level"
        )

    def list(self, request, *args, **kwargs):
        profile = ProfessionalProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(
                {"success": False, "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = ProfessionalProfileSerializer(profile).data
        return Response(
            {"success": True, "data": data},
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        profile = ProfessionalProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(
                {"success": False, "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data.get("data")
        if data:
            data = json.loads(data)
        else:
            data = {}
        profile_image = request.FILES.get("profile_image")
        if profile_image:
            request.user.upload_profile_image(profile_image)

        serializer = ProfessionalProfileUpsertSerializer(
            profile, data=data, partial=True
        )
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        try:
            cache.delete(recommendation_key(request.user.id))
        except Exception:
            pass
        out = ProfessionalProfileSerializer(profile).data
        return Response(
            {
                "success": True,
                "message": "Professional profile updated",
                "data": out,
            },
            status=status.HTTP_200_OK,
        )


class ParentProfileViewSet(ModelViewSet):
    """
    Parent-specific profile endpoint
    Endpoints:
    - GET   /api/parent-profile/
    - PATCH /api/parent-profile/
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get", "patch", "head", "options"]
    lookup_value_regex = r'[0-9]+'

    throttle_classes = [PerUserBurstRateThrottle]

    def get_queryset(self):
        return (
            ParentProfile.objects.filter(user=self.request.user)
            .select_related("user__country", "user__states", "user__city")
            .prefetch_related("language")
        )

    def list(self, request, *args, **kwargs):
        profile = ParentProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(
                {"success": False, "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = ParentProfileSerializer(profile).data
        return Response(
            {"success": True, "data": data},
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        profile = ParentProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(
                {"success": False, "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data.get("data")
        if data:
            data = json.loads(data)
        else:
            data = {}
        profile_image = request.FILES.get("profile_image")
        if profile_image:
            request.user.upload_profile_image(profile_image)

        serializer = ParentProfileUpsertSerializer(profile, data=data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        try:
            cache.delete(recommendation_key(request.user.id))
        except Exception:
            pass
        out = ParentProfileSerializer(profile).data
        return Response(
            {
                "success": True,
                "message": "Parent profile updated",
                "data": out,
            },
            status=status.HTTP_200_OK,
        )

class InstituteProfileViewSet(OrganizationProfileViewSet):
    profile_model = InstituteProfile
    read_serializer_class = InstituteProfileSerializer
    update_serializer_class = InstituteProfileUpSerializer


class InstituteGalleryViewSet(OrganizationGalleryViewSet):
    profile_model = InstituteProfile
    gallery_model = InstituteGallery
    profile_fk_field = "institute"
    gallery_serializer_class = InstituteGallerySerializer
    profile_not_found_message = "Institute profile not found"


class SchoolCollegeProfileViewSet(OrganizationProfileViewSet):
    profile_model = SchoolCollegeProfile
    read_serializer_class = SchoolCollegeProfileSerializer
    update_serializer_class = SchoolCollegeProfileUpSerializer


class SchoolCollegeGalleryViewSet(OrganizationGalleryViewSet):
    profile_model = SchoolCollegeProfile
    gallery_model = SchoolCollegeGallery
    profile_fk_field = "school_college"
    gallery_serializer_class = SchoolCollegeGallerySerializer
    profile_not_found_message = "School / college profile not found"


class CorporateProfileViewSet(OrganizationProfileViewSet):
    profile_model = CorporateProfile
    read_serializer_class = CorporateProfileSerializer
    update_serializer_class = CorporateProfileUpSerializer


class CorporateGalleryViewSet(OrganizationGalleryViewSet):
    profile_model = CorporateProfile
    gallery_model = CorporateGallery
    profile_fk_field = "corporate"
    gallery_serializer_class = CorporateGallerySerializer
    profile_not_found_message = "Corporate profile not found"
