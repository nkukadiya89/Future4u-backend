from django.utils import timezone
import os
import tempfile
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404
from email_utils.send_email import send_activation_password_setup_email
from user.admin_user_serializers import AdminStudentSerializer,AdminStudentSortSerializer, BulkUserUploadSerializer
from user.models import User
from user.permissions import IsAdminUser
from user.services.bulk_user_upload import BulkUserUploadService
from user.tasks import bulk_upload_user_task
from user_profile.models import InstituteProfile, StudentProfile, SchoolCollegeProfile,CorporateProfile
from rest_framework.viewsets import ModelViewSet
from user_profile.serializers import StudentProfileSerializer
from user_profile.serializers import SchoolCollegeProfileSerializer,InstituteProfileSerializer,CorporateProfileSerializer
from user.admin_school_colleges_serializers import AdminSchoolCollegesSerializer,AdminSchoolCollegeSortSerializer
from user.admin_institute_serializers import AdminInstituteSerializer,AdminInstituteSortSerializer
from user.admin_corporate_serializers import AdminCorporateSerializer,AdminCorporateSortSerializer

class BaseAdminProfileViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [JWTAuthentication]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    user_role = None
    role_name = None
    profile_model = None
    detail_serializer_class = None
    archive_serializer_class = None

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

        return Response({
            "success": True,
            "data": serializer.data,
        })

    def create(self, request):
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
        )

        if serializer.is_valid():
            user = serializer.save()
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

        return Response(
            {
                "success": True,
                "message": f"{self.role_name} deleted successfully",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"], url_path="update-status")
    @transaction.atomic
    def update_status(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        status_value = request.data.get("status")

        if status_value not in ["active", "inactive"]:
            return Response(
                {
                    "success": False,
                    "message": "Status must be active or inactive",
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

        if user.status == status_value:
            return Response(
                {
                    "success": False,
                    "message": f"{self.role_name} is already {status_value}.",
                },
                status=status.HTTP_200_OK,
            )

        user.status = status_value
        user.is_active = status_value == "active"
        user.updated_by = request.user
        user.updated_at = timezone.now()

        user.save(
            update_fields=[
                "status",
                "is_active",
                "updated_by",
                "updated_at",
            ]
        )

        if status_value == "active":
            send_activation_password_setup_email(user)

        return Response(
            {
                "success": True,
                "message": f"{self.role_name} status updated to {status_value} successfully.",
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

        return Response(
            {
                "success": True,
                "message": f"{self.role_name} deleted successfully",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="archive-list")
    def archive_list(self, request, *args, **kwargs):
        queryset = self.profile_model.objects.select_related("user").filter(
            user__user_type=self.user_role,
            user__deleted=True,
        ).order_by("-user__deleted_at")

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.archive_serializer_class(page, many=True)
            return self.get_paginated_response(
                {
                    "success": True,
                    "data": serializer.data,
                }
            )

        serializer = self.archive_serializer_class(queryset, many=True)

        return Response(
            {
                "success": True,
                "data": serializer.data,
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

        return Response(
            {
                "success": True,
                "message": f"{self.role_name}s restored successfully",
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
    archive_serializer_class = StudentProfileSerializer

class AdminSchoolCollegeViewSet(BaseAdminProfileViewSet):
    user_role = User.Role.SCHOOL_COLLEGE
    role_name = "School College"
    profile_model = SchoolCollegeProfile
    serializer_class = AdminSchoolCollegesSerializer
    detail_serializer_class = AdminSchoolCollegeSortSerializer
    archive_serializer_class = SchoolCollegeProfileSerializer

class AdminInstituteViewSet(BaseAdminProfileViewSet):
    user_role = User.Role.INSTITUTE
    role_name = "Institute"
    profile_model = InstituteProfile
    serializer_class = AdminInstituteSerializer
    detail_serializer_class = AdminInstituteSortSerializer
    archive_serializer_class = InstituteProfileSerializer

class AdminCorporateViewSet(BaseAdminProfileViewSet):
    user_role = User.Role.CORPORATE
    role_name = "Corporate"
    profile_model = CorporateProfile
    serializer_class = AdminCorporateSerializer
    detail_serializer_class = AdminCorporateSortSerializer
    archive_serializer_class = CorporateProfileSerializer
