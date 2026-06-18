from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from assessment.models import ParentAssessment
from assessment.serializers import ParentAssessmentSerializer
from utils.pagination import Pagination


def calculate_parent_screen(assessment):
    """Determine the next screen based on what data is missing."""
    if assessment.is_completed:
        return ParentAssessment.Screen.COMPLETE

    if not assessment.domain_category_id:
        return ParentAssessment.Screen.DOMAIN_CATEGORY
    if not assessment.career_direction.exists():
        return ParentAssessment.Screen.CAREER_DIRECTION
    if not assessment.parent_support:
        return ParentAssessment.Screen.PARENT_SUPPORT
    if not assessment.concerns.exists():
        return ParentAssessment.Screen.CONCERNS
    if not assessment.parent_career_expectations.exists():
        return ParentAssessment.Screen.PARENT_CAREER_EXPECTATIONS
    if not assessment.limitations.exists():
        return ParentAssessment.Screen.LIMITATIONS
    if not assessment.career_familiarity:
        return ParentAssessment.Screen.CAREER_FAMILIARITY
    if not assessment.decision_style:
        return ParentAssessment.Screen.DECISION_STYLE
    if not assessment.career_values.exists():
        return ParentAssessment.Screen.CAREER_VALUES
    if not assessment.user_goals.exists():
        return ParentAssessment.Screen.USER_GOALS

    return ParentAssessment.Screen.COMPLETE


def sync_parent_screen(assessment):
    """Calculate and update current_screen if changed."""
    next_screen = calculate_parent_screen(assessment)
    if assessment.current_screen != next_screen:
        assessment.current_screen = next_screen
        assessment.save(update_fields=["current_screen"])
    return assessment


def assessment_status_payload(assessment):
    """Build status response dict."""
    if not assessment:
        return {
            "success": True,
            "has_assessment": False,
            "assessment_id": None,
            "is_completed": False,
            "current_screen": ParentAssessment.Screen.DOMAIN_CATEGORY,
            "data": None,
        }

    return {
        "success": True,
        "has_assessment": True,
        "assessment_id": assessment.id,
        "is_completed": assessment.is_completed,
        "current_screen": calculate_parent_screen(assessment),
        "data": {
            "domain_category": (
                str(assessment.domain_category_id)
                if assessment.domain_category_id
                else None
            ),
        },
    }


class ParentAssessmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    serializer_class = ParentAssessmentSerializer

    def get_queryset(self):
        return ParentAssessment.objects.filter(
            user=self.request.user,
            deleted=False,
        )

    search_fields = [
        "id",
        "domain_category__domain_name",
        "parent_support",
        "career_familiarity",
        "decision_style",
        "is_completed",
    ]
    ordering_fields = [
        "user",
        "domain_category",
        "parent_support",
        "created_at",
        "updated_at",
        "is_completed",
    ]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        force_new = request.data.get("force_new") is True
        if not force_new:
            assessment = self.get_queryset().filter(is_completed=False).first()
            if assessment:
                sync_parent_screen(assessment)
                serializer = self.get_serializer(assessment)
                return Response(
                    {
                        "success": True,
                        "message": "Assessment resumed",
                        "resume": True,
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

        assessment = ParentAssessment(user=request.user, is_completed=False)
        assessment._request_user = request.user
        assessment.save()
        sync_parent_screen(assessment)
        serializer = self.get_serializer(assessment)
        return Response(
            {
                "success": True,
                "message": "Assessment created",
                "resume": False,
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        instance._request_user = self.request.user
        assessment = serializer.save()
        sync_parent_screen(assessment)
        return assessment

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assessment = self.perform_update(serializer)
        serializer = self.get_serializer(assessment)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="status")
    def assessment_status(self, request):
        assessment = self.get_queryset().order_by("-created_at").first()
        return Response(assessment_status_payload(assessment))

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """POST /api/parent/assessments/{id}/complete/"""
        assessment = self.get_object()
        with transaction.atomic():
            assessment.is_completed = True
            assessment.current_screen = ParentAssessment.Screen.COMPLETE
            assessment._request_user = request.user
            assessment.updated_by = request.user
            assessment.updated_at = timezone.now()
            assessment.save(
                update_fields=[
                    "is_completed",
                    "current_screen",
                    "updated_at",
                    "updated_by",
                ]
            )
        return Response(
            {
                "success": True,
                "message": "Assessment completed",
                "data": {
                    "id": assessment.id,
                    "current_screen": assessment.current_screen,
                    "is_completed": True,
                },
            },
            status=status.HTTP_200_OK,
        )
