from collections import defaultdict

from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.services import log_event
from user_profile.models import ChildProfile
from subscription.services.usage import consume_feature
from utils.token_check import check_and_deduct_token

from assessment.models import ParentAssessment
from assessment.serializers import (
    ParentAssessmentSerializer,
    ParentAssessmentWriteSerializer,
)
from utils.pagination import Pagination


def calculate_parent_screen(assessment):
    """Determine the next screen based on what data is missing."""
    if assessment.is_completed:
        return ParentAssessment.Screen.COMPLETE

    if not assessment.domain_category_id:
        return ParentAssessment.Screen.DOMAIN_CATEGORY
    if not assessment.domain_id:
        return ParentAssessment.Screen.DOMAIN
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
        "child_id": assessment.child_id,
        "is_completed": assessment.is_completed,
        "current_screen": calculate_parent_screen(assessment),
        "data": {
            "domain_category": (
                str(assessment.domain_category_id)
                if assessment.domain_category_id
                else None
            ),
            "domain": (str(assessment.domain_id) if assessment.domain_id else None),
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

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ParentAssessmentWriteSerializer
        return ParentAssessmentSerializer

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
        child_id = request.data.get("child")

        if not child_id:
            return Response(
                {"success": False, "message": "child is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ChildProfile.objects.filter(
            id=child_id,
            parent_profile__user=request.user,
            deleted=False,
        ).exists():
            return Response(
                {"success": False, "message": "Invalid child selected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        force_new = request.data.get("force_new") is True
        if not force_new:
            assessment = (
                self.get_queryset()
                .filter(is_completed=False, child_id=child_id)
                .first()
            )
            if assessment:
                sync_parent_screen(assessment)
                serializer = ParentAssessmentSerializer(
                    assessment, context=self.get_serializer_context()
                )
                return Response(
                    {
                        "success": True,
                        "message": "Assessment resumed",
                        "resume": True,
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

        try:
            check_and_deduct_token(request.user, "assessment")
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        assessment = ParentAssessment(
            user=request.user,
            child_id=child_id,
            is_completed=False,
        )
        assessment._request_user = request.user
        assessment.save()
        sync_parent_screen(assessment)
        consume_feature(request.user, "assessment", 1)
        serializer = ParentAssessmentSerializer(
            assessment, context=self.get_serializer_context()
        )
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

        # Validate child ownership if being updated
        child_id = request.data.get("child")
        if child_id:
            if not ChildProfile.objects.filter(
                id=child_id,
                parent_profile__user=request.user,
                deleted=False,
            ).exists():
                return Response(
                    {"success": False, "message": "Invalid child selected"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assessment = self.perform_update(serializer)
        serializer = ParentAssessmentSerializer(
            assessment, context=self.get_serializer_context()
        )
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        """
        GET /api/parent/assessments/dashboard/
        Returns all children with their assessments and progress.
        """
        # Get all children for this parent
        children = ChildProfile.objects.filter(
            parent_profile__user=request.user,
            deleted=False,
        ).select_related("education_level", "stream")

        # Screen order for progress calculation (from model choices)
        screen_order = [choice[0] for choice in ParentAssessment.Screen.choices]
        total_screens = len(screen_order) - 1  # Exclude COMPLETE from total

        # Fetch ALL assessments in a single query (avoid N+1)
        all_assessments = (
            ParentAssessment.objects.filter(
                user=request.user,
                deleted=False,
            )
            .select_related("domain_category")
            .order_by("-created_at")
        )

        # Group by child_id in Python
        assessments_by_child = defaultdict(list)
        for a in all_assessments:
            assessments_by_child[a.child_id].append(a)

        children_data = []
        total_assessments = 0
        completed_count = 0

        for child in children:
            assessments = assessments_by_child.get(child.id, [])

            assessment_list = []
            for assessment in assessments:
                # Calculate progress
                if (
                    assessment.is_completed
                    or assessment.current_screen == ParentAssessment.Screen.COMPLETE
                ):
                    progress = 100
                else:
                    current_index = 0
                    for i, screen in enumerate(screen_order):
                        if assessment.current_screen == screen:
                            current_index = i
                            break
                    progress = min(int((current_index / total_screens) * 100), 99)

                assessment_list.append(
                    {
                        "id": assessment.id,
                        "domain_category_name": (
                            assessment.domain_category.domain_name
                            if assessment.domain_category_id
                            else None
                        ),
                        "current_screen": assessment.current_screen,
                        "progress_percentage": progress,
                        "is_completed": assessment.is_completed,
                        "created_at": assessment.created_at,
                    }
                )

                total_assessments += 1
                if assessment.is_completed:
                    completed_count += 1

            children_data.append(
                {
                    "child_id": child.id,
                    "full_name": str(child),
                    "first_name": child.first_name,
                    "last_name": child.last_name,
                    "profile_image": child.profile_image,
                    "education_level": child.education_level_id,
                    "education_level_name": (
                        child.education_level.display_name
                        if child.education_level
                        else None
                    ),
                    "stream": child.stream_id,
                    "stream_name": child.stream.stream_name if child.stream else None,
                    "assessments": assessment_list,
                }
            )

        return Response(
            {
                "success": True,
                "data": {
                    "children": children_data,
                    "totals": {
                        "total_assessments": total_assessments,
                        "completed": completed_count,
                        "in_progress": total_assessments - completed_count,
                    },
                },
            }
        )

    @action(detail=False, methods=["get"], url_path="status")
    def assessment_status(self, request):
        qs = self.get_queryset()
        child_id = request.query_params.get("child_id")
        if child_id:
            qs = qs.filter(child_id=child_id)
        assessment = qs.order_by("-created_at").first()
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
