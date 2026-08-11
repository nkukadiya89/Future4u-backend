import os
import tempfile
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from activity_log.services import log_event
from common.master_view import BaseModelViewSet
from user.admin_user_serializers import BulkUserUploadSerializer
from user.models import User
from user.services.bulk_user_upload import BulkUserUploadService
from user.tasks import bulk_upload_user_task
from utils.datetime_formatter import format_datetime
from utils.pagination import Pagination
from .organization_professional_serializers import (
    OrganizationProfessionalCreateSerializer,
    OrganizationProfessionalListSerializer,
)
from .permissions import IsCorporate

class OrganizationProfessionalViewSet(BaseModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsCorporate]
    pagination_class = Pagination
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = BaseModelViewSet.searching_fields + [
        "first_name",
        "last_name",
        "user_type",
        "email",
        "email_verified",
        "must_change_password",
        "phone",
        "address",
        "country__name",
        "states__name",
        "city__name",
        "is_active",
        "status",
    ]

    ordering_fields = BaseModelViewSet.ordering_fields + [
        "id",
        "first_name",
        "last_name",
        "user_type",
        "email",
        "email_verified",
        "must_change_password",
        "phone",
        "address",
        "country",
        "states",
        "city",
        "profile_image",
        "is_active",
        "status",
    ]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.filter(
            Q(created_by=user) | Q(professional_profile__referred_by=user),
            user_type=User.Role.PROFESSIONAL,
            deleted=False,
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return (
            queryset.select_related(
                "country",
                "states",
                "city",
                "professional_profile",
                "professional_profile__education_level",
            )
            .order_by("-id")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return OrganizationProfessionalCreateSerializer
        return OrganizationProfessionalListSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid(raise_exception=True):
            professional = serializer.save()
            log_event(
                event="professional.created",
                description=f"Created professional {professional.email}",
                user=request.user,
                entity_type="user",
                entity_id=professional.id,
                metadata={
                    "professional_name": (
                        f"{professional.first_name} {professional.last_name}"
                    )
                },
                request=request,
            )
            return Response(
                {
                    "success": True,
                    "message": (
                        "Working Professional created successfully. "
                        "A password setup link has been sent to their email."
                    ),
                    "professional_id": professional.id,
                    "must_change_password": True,
                    "created_by": professional.created_by_id,
                    "created_at": format_datetime(professional.created_at),
                },
                status=status.HTTP_201_CREATED,
            )

    def retrieve(self, request, *args, **kwargs):
        professional = self.get_object()
        serializer = self.get_serializer(professional)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="bulk-upload")
    def bulk_upload(self, request, *args, **kwargs):
        serializer = BulkUserUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            uploaded_file = serializer.validated_data["file"]

            df = BulkUserUploadService._read_file(uploaded_file)
            required_columns = BulkUserUploadService.get_required_columns(
                User.Role.PROFESSIONAL, skip_referral=True
            )
            BulkUserUploadService._validate_headers(df, required_columns)

            uploaded_file.seek(0)

            suffix = os.path.splitext(uploaded_file.name)[1]

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)

            bulk_upload_user_task.delay(
                tmp.name,
                request.user.id,
                User.Role.PROFESSIONAL,
                skip_referral=True,
                skip_profile_fields=True,
            )

            log_event(
                event="professional.bulk_upload",
                description=f"Started bulk upload: {uploaded_file.name}",
                user=request.user,
                entity_type="user",
                entity_id=None,
                metadata={"filename": uploaded_file.name},
                request=request,
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        f"Bulk Upload Started. Your file '{uploaded_file.name}' "
                        "has started processing."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(
                {
                    "success": False,
                    "message": "".join(e.message) if hasattr(e, "message") else str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
