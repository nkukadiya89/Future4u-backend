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
from assessment.models import StudentAssessment
from assessment.serializers import StudentAssessmentSerializer
from assessment_career.models import CareerRecommendation, CareerSuggestion
from assessment_career.serializers import (
    CareerRecommendationSerializer,
    CareerSuggestionSerializer,
)
from common.master_view import BaseModelViewSet
from user.admin_user_serializers import BulkUserUploadSerializer
from user.models import User
from user.services.bulk_user_upload import BulkUserUploadService
from user.tasks import bulk_upload_user_task
from utils.pagination import Pagination

from .permissions import IsSchoolCollegeOrInstitute
from .student_organization_serializers import (
    OrganizationStudentCreateSerializer,
    OrganizationStudentListSerializer,
)


class OrganizationStudentViewSet(BaseModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsSchoolCollegeOrInstitute]
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
        return (
            User.objects.filter(
                Q(created_by=user) | Q(student_profile__referred_by=user),
                user_type=User.Role.STUDENT,
                deleted=False,
            )
            .select_related(
                "country",
                "states",
                "city",
                "student_profile",
                "student_profile__education_level",
            )
            .prefetch_related(
                "student_assessments",
                "career_recommendations",
                "career_recommendations__suggestions",
            )
            .order_by("-id")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return OrganizationStudentCreateSerializer
        if self.action == "student_assessment":
            return StudentAssessmentSerializer
        if self.action == "student_suggestion":
            return CareerSuggestionSerializer
        return OrganizationStudentListSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid(raise_exception=True):
            student = serializer.save()
            log_event(
                event="student.created",
                description=f"Created student {student.email}",
                user=request.user,
                entity_type="user",
                entity_id=student.id,
                metadata={"student_name": f"{student.first_name} {student.last_name}"},
                request=request,
            )
            return Response(
                {
                    "success": True,
                    "message": "Student created successfully. A password setup link has been sent to their email.",
                    "student_id": student.id,
                    "must_change_password": True,
                    "created_by": student.created_by_id,
                    "created_at": student.created_at,
                },
                status=status.HTTP_201_CREATED,
            )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        student = self.get_object()
        serializer = self.get_serializer(student)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="assessments")
    def student_assessment(self, request, pk=None):
        student = self.get_object()
        log_event(
            event="student.assessment_viewed",
            description=f"Viewed {student.email}'s assessments",
            user=request.user,
            entity_type="user",
            entity_id=student.id,
            request=request,
        )
        queryset = StudentAssessment.objects.filter(
            user=student, deleted=False
        ).order_by("-created_at")
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {
                    "success": True,
                    "data": serializer.data,
                },
            )

        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response(
            {
                "success": True,
                "data": serializer.data,
            },
        )

    @action(detail=True, methods=["get"], url_path="recommendation")
    def student_recommendation(self, request, pk=None):
        assessment_id = request.query_params.get("assessment_id")
        if not assessment_id:
            return Response(
                {
                    "success": False,
                    "message": "Assessment id is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        student = self.get_object()
        log_event(
            event="student.recommendation_viewed",
            description=f"Viewed {student.email}'s recommendation",
            user=request.user,
            entity_type="user",
            entity_id=student.id,
            request=request,
        )
        assessment = StudentAssessment.objects.filter(
            id=assessment_id, user=student, deleted=False
        ).first()
        if not assessment:
            return Response(
                {
                    "success": False,
                    "message": "Assessment not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        recommendation = (
            CareerRecommendation.objects.filter(
                student_assessment=assessment, deleted=False
            )
            .prefetch_related("suggestions")
            .first()
        )
        if not recommendation:
            return Response(
                {
                    "success": False,
                    "message": "Recommendation not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CareerRecommendationSerializer(recommendation)
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
                User.Role.STUDENT
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
                User.Role.STUDENT,
                forced_referred_by=request.user.id,
            )

            log_event(
                event="student.bulk_upload",
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

    @action(detail=True, methods=["get"], url_path="suggestion")
    def student_suggestion(self, request, pk=None):
        suggestion_id = request.query_params.get("suggestion_id")
        if not suggestion_id:
            return Response(
                {
                    "success": False,
                    "message": "Suggestion id is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        student = self.get_object()
        suggestion = (
            CareerSuggestion.objects.filter(
                id=suggestion_id,
                deleted=False,
                recommendation__user=student,
                recommendation__profile_type="student",
            )
            .select_related("recommendation")
            .first()
        )
        if not suggestion:
            return Response(
                {
                    "success": False,
                    "message": "Suggestion not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(suggestion)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
