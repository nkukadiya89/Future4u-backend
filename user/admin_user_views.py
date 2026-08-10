import os
import tempfile
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from activity_log.services import log_event
from email_utils.send_email import send_activation_password_setup_email
from user.admin_corporate_serializers import (
    AdminCorporateSerializer,
    AdminCorporateSortSerializer,
)
from user.admin_institute_serializers import (
    AdminInstituteSerializer,
    AdminInstituteSortSerializer,
)
from user.admin_school_colleges_serializers import (
    AdminSchoolCollegeSortSerializer,
    AdminSchoolCollegesSerializer,
)
from user.admin_user_serializers import (
    AdminStudentSerializer,
    AdminStudentSortSerializer,
    BulkUserUploadSerializer,
)
from user.admin_working_professional_serializers import (
    AdminWorkingProfessionalSerializer,
    AdminWorkingProfessionalSortSerializer,
)
from user.models import User
from user.permissions import IsAdminUser
from user.serializers import UserListSerializer
from user.services.bulk_user_upload import BulkUserUploadService
from user.tasks import bulk_upload_user_task
from user_profile.models import (
    CorporateProfile,
    InstituteProfile,
    ProfessionalProfile,
    SchoolCollegeProfile,
    StudentProfile,
)
from utils.pagination import Pagination
from utils.token_check import _check_org_monthly_reset


class BaseAdminProfileViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [JWTAuthentication]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    user_role = None
    role_name = None
    profile_model = None
    detail_serializer_class = None

    def get_queryset(self):
        return User.objects.filter(
            user_type=self.user_role,
            deleted=False,
        )

    def get_user(self, pk, include_deleted=False):
        queryset = User.objects.filter(
            id=pk,
            user_type=self.user_role,
        )
        if not include_deleted:
            queryset = queryset.filter(deleted=False)
        return queryset.first()

    def retrieve(self, request, pk=None):
        profile = self.profile_model.objects.filter(
            user_id=pk,
            user__user_type=self.user_role,
            user__deleted=False,
        ).first()

        if not profile:
            return Response(
                {
                    "success": False,
                    "message": f"{self.role_name} profile not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.detail_serializer_class(profile)

        return Response(
            {
                "success": True,
                "data": serializer.data,
            }
        )

    def create(self, request):
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
        )

        if serializer.is_valid():
            user = serializer.save()
            log_event(
                event="user.created",
                description=f"Created {self.role_name} {user.email}",
                user=request.user,
                entity_type="user",
                entity_id=user.id,
                request=request,
            )
            return Response(
                {
                    "success": True,
                    "message": f"{self.role_name} created. A password setup link has been sent to their email.",
                    "user_id": user.id,
                    "user_type": user.user_type,
                    "must_change_password": True,
                    "created_by": user.created_by_id,
                    "created_at": user.created_at,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def partial_update(self, request, pk=None):
        user = self.get_user(pk)

        if not user:
            return Response(
                {
                    "success": False,
                    "message": f"{self.role_name} not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.serializer_class(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            user = serializer.save()
            log_event(
                event="user.updated",
                description=f"Updated {self.role_name} {user.email}",
                user=request.user,
                entity_type="user",
                entity_id=user.id,
                request=request,
            )
            return Response(
                {
                    "success": True,
                    "message": f"{self.role_name} updated successfully",
                    "user_id": user.id,
                    "user_type": user.user_type,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        user = self.get_user(pk, include_deleted=True)

        if not user:
            return Response(
                {
                    "success": False,
                    "message": f"{self.role_name} not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.deleted:
            return Response(
                {
                    "success": False,
                    "message": f"{self.role_name} is already archived.",
                },
                status=status.HTTP_200_OK,
            )

        if user.status == "active":
            return Response(
                {
                    "success": False,
                    "message": f"Active {self.role_name.lower()} can not delete. Please inactive this {self.role_name.lower()} first.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.deleted = True
        user.deleted_at = timezone.now()
        user.deleted_by = request.user
        user.save(update_fields=["deleted", "deleted_at", "deleted_by"])

        log_event(
            event="user.deleted",
            description=f"Deleted {self.role_name} {user.email}",
            user=request.user,
            entity_type="user",
            entity_id=user.id,
            request=request,
        )

        return Response(
            {
                "success": True,
                "message": f"{self.role_name} deleted successfully",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["patch"], url_path="update-status")
    @transaction.atomic
    def update_status(self, request, *args, **kwargs):
        ids = request.data.get("ids", [])
        new_status = request.data.get("status")

        if not isinstance(ids, list) or not ids:
            return Response(
                {"success": False, "message": "ids must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status not in ["active", "inactive"]:
            return Response(
                {
                    "success": False,
                    "message": "Status must be active or inactive",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        users = self.get_queryset().filter(id__in=ids)

        found_ids = set(users.values_list("id", flat=True))
        not_found_ids = list(set(ids) - found_ids)

        skipped_ids = []
        updated_ids = []
        activated_users = []

        for user in users:
            if user.status == new_status:
                skipped_ids.append(user.id)
                continue

            old_status = user.status

            user.status = new_status
            user.is_active = new_status == "active"
            user.updated_by = request.user
            user.updated_at = timezone.now()

            user.save(
                update_fields=[
                    "status",
                    "is_active",
                    "updated_at",
                    "updated_by",
                ]
            )

            updated_ids.append(user.id)
            if old_status in ["pending", "inactive"] and new_status == "active":
                activated_users.append(user)

            log_event(
                event="user.status_changed",
                description=f"Changed {self.role_name} {user.email} status from {old_status} to {new_status}",
                user=request.user,
                entity_type="user",
                entity_id=user.id,
                request=request,
            )

        if activated_users:
            transaction.on_commit(
                lambda: [
                    send_activation_password_setup_email(user)
                    for user in activated_users
                ]
            )

        return Response(
            {
                "success": True,
                "message": f"{len(updated_ids)} user(s) updated successfully.",
                "data": {
                    "updated_ids": updated_ids,
                    "skipped_ids": skipped_ids,
                    "not_found_ids": not_found_ids,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["patch"], url_path="bulk-archive")
    @transaction.atomic
    def bulk_archive(self, request, *args, **kwargs):
        ids = request.data.get("ids", [])

        if not isinstance(ids, list) or not ids:
            return Response(
                {
                    "success": False,
                    "message": "ids must be a non-empty array",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        users = User.objects.filter(
            id__in=ids,
            user_type=self.user_role,
        )

        if not users.exists():
            return Response(
                {
                    "success": False,
                    "message": f"{self.role_name} not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if users.filter(deleted=True).exists():
            return Response(
                {
                    "success": False,
                    "message": f"Some {self.role_name.lower()} are already archived.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if users.filter(status="active").exists():
            return Response(
                {
                    "success": False,
                    "message": f"Active {self.role_name.lower()} can not delete. Please inactive first.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        users.update(
            deleted=True,
            deleted_at=timezone.now(),
            deleted_by=request.user,
        )

        log_event(
            event="user.bulk_archive",
            description=f"Bulk archived {users.count()} {self.role_name}(s)",
            user=request.user,
            entity_type="user",
            entity_id=None,
            metadata={"user_ids": ids, "count": users.count()},
            request=request,
        )

        return Response(
            {
                "success": True,
                "message": f"{self.role_name} deleted successfully",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["patch"], url_path="bulk-restore")
    @transaction.atomic
    def bulk_restore(self, request, *args, **kwargs):
        ids = request.data.get("ids", [])

        if not isinstance(ids, list) or not ids:
            return Response(
                {
                    "success": False,
                    "message": "ids must be a non-empty array",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        users = User.objects.filter(
            id__in=ids,
            user_type=self.user_role,
        )

        if not users.exists():
            return Response(
                {
                    "success": False,
                    "message": f"{self.role_name} not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if users.filter(deleted=False).exists():
            return Response(
                {
                    "success": False,
                    "message": f"Some {self.role_name.lower()} are already active",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        users.update(
            deleted=False,
            deleted_at=None,
            deleted_by=None,
            updated_at=timezone.now(),
            updated_by=request.user,
        )

        log_event(
            event="user.bulk_restore",
            description=f"Bulk restored {users.count()} {self.role_name}(s)",
            user=request.user,
            entity_type="user",
            entity_id=None,
            metadata={"user_ids": ids, "count": users.count()},
            request=request,
        )

        return Response(
            {
                "success": True,
                "message": f"{self.role_name}s restored successfully",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"], url_path="update-tokens")
    def update_tokens(self, request, pk=None):
        extra = request.data.get("extra_token_limit")
        if extra is None or not isinstance(extra, int) or extra < 0:
            return Response(
                {
                    "success": False,
                    "message": "extra_token_limit must be a non-negative integer",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = self.get_user(pk)
        if not user:
            return Response(
                {
                    "success": False,
                    "message": f"{self.role_name} not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_org_staff:
            return Response(
                {
                    "success": False,
                    "message": "Organization staff cannot have a personal token pool.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = self.profile_model.objects.filter(user=user).first()
        if not profile:
            return Response(
                {
                    "success": False,
                    "message": f"{self.role_name} profile not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            profile = (
                self.profile_model.objects.select_for_update().get(id=profile.id)
            )
            _check_org_monthly_reset(profile, user.user_type)

            previous_extra = profile.extra_token_limit or 0
            before_token = profile.token_limit or 0
            profile.extra_token_limit = previous_extra + extra
            profile.token_limit = before_token + extra
            profile.save(update_fields=["extra_token_limit", "token_limit"])

        log_event(
            event="user.tokens_updated",
            description=(
                f"Added {extra} extra tokens " f"to {self.role_name} {user.email}"
            ),
            user=request.user,
            entity_type="user",
            entity_id=user.id,
            metadata={
                "previous_extra": previous_extra,
                "new_extra": profile.extra_token_limit,
                "token_increase": extra,
                "token_limit_before": before_token,
                "token_limit_after": profile.token_limit,
            },
            request=request,
        )

        return Response(
            {
                "success": True,
                "message": f"{extra} extra tokens added to {self.role_name}.",
                "data": {
                    "extra_token_limit": profile.extra_token_limit,
                    "token_limit": profile.token_limit,
                    "last_token_reset_at": profile.last_token_reset_at,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="bulk-upload")
    def bulk_upload_users(self, request):
        serializer = BulkUserUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            uploaded_file = serializer.validated_data["file"]

            df = BulkUserUploadService._read_file(uploaded_file)
            user_type = serializer.validated_data.get("user_type", self.user_role)

            required_columns = BulkUserUploadService.get_required_columns(user_type)
            BulkUserUploadService._validate_headers(df, required_columns)

            uploaded_file.seek(0)

            suffix = os.path.splitext(uploaded_file.name)[1]

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)

            bulk_upload_user_task.delay(
                tmp.name,
                request.user.id,
                user_type,
            )

            log_event(
                event="user.bulk_upload",
                description=f"Started bulk upload for {user_type}: {uploaded_file.name}",
                user=request.user,
                entity_type="user",
                entity_id=None,
                metadata={"filename": uploaded_file.name, "user_type": user_type},
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


class AdminStudentViewSet(BaseAdminProfileViewSet):
    user_role = User.Role.STUDENT
    role_name = "Student"
    profile_model = StudentProfile
    serializer_class = AdminStudentSerializer
    detail_serializer_class = AdminStudentSortSerializer


class AdminSchoolCollegeViewSet(BaseAdminProfileViewSet):
    user_role = User.Role.SCHOOL_COLLEGE
    role_name = "School College"
    profile_model = SchoolCollegeProfile
    serializer_class = AdminSchoolCollegesSerializer
    detail_serializer_class = AdminSchoolCollegeSortSerializer


class AdminInstituteViewSet(BaseAdminProfileViewSet):
    user_role = User.Role.INSTITUTE
    role_name = "Institute"
    profile_model = InstituteProfile
    serializer_class = AdminInstituteSerializer
    detail_serializer_class = AdminInstituteSortSerializer


class AdminCorporateViewSet(BaseAdminProfileViewSet):
    user_role = User.Role.CORPORATE
    role_name = "Corporate"
    profile_model = CorporateProfile
    serializer_class = AdminCorporateSerializer
    detail_serializer_class = AdminCorporateSortSerializer


class AdminWorkingProfessionalViewSet(BaseAdminProfileViewSet):
    user_role = User.Role.PROFESSIONAL
    role_name = "Working Professional"
    profile_model = ProfessionalProfile
    serializer_class = AdminWorkingProfessionalSerializer
    detail_serializer_class = AdminWorkingProfessionalSortSerializer


class AdminUserArchiveViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    serializer_class = UserListSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    http_method_names = ["get", "head", "options"]

    search_fields = [
        "id",
        "first_name",
        "last_name",
        "full_name",
        "email",
        "phone",
        "user_type",
        "states__name",
        "city__name",
        "deleted_by__first_name",
        "deleted_by__last_name",
        "deleted_by__full_name",
        "deleted_at",
    ]

    ordering_fields = [
        "id",
        "first_name",
        "last_name",
        "full_name",
        "email",
        "phone",
        "user_type",
        "states",
        "city",
        "deleted_by",
        "deleted_at",
        "created_at",
    ]

    def get_queryset(self):
        queryset = (
            User.objects.filter(deleted=True)
            .select_related(
                "country",
                "states",
                "city",
                "created_by",
                "updated_by",
                "deleted_by",
            )
            .order_by("-deleted_at")
        )

        user_type = self.request.query_params.get("user_type")
        if user_type:
            queryset = queryset.filter(user_type=user_type)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = UserListSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = UserListSerializer(page, many=True)
            return self.get_paginated_response(
                {
                    "success": True,
                    "data": serializer.data,
                }
            )

        serializer = UserListSerializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
