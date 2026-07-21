from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.services import log_event
from assessment.models import ProfessionalAssessment
from subscription.services.usage import consume_feature
from utils.token_check import check_token_available
from assessment.serializers import (
    ProfessionalAssessmentSerializer,
    ProfessionalAssessmentWriteSerializer,
)
from utils.pagination import Pagination


def get_professional_profile(user):
    try:
        from user_profile.models import ProfessionalProfile

        return ProfessionalProfile.objects.select_related(
            "education_level",
            "stream",
        ).get(user=user)
    except ProfessionalProfile.DoesNotExist:
        return None


def calculate_professional_screen(assessment):
    if assessment.is_completed:
        return ProfessionalAssessment.Screen.COMPLETE

    if not assessment.career_intention:
        return ProfessionalAssessment.Screen.CAREER_INTENTION
    if not assessment.guidance_reasons.exists():
        return ProfessionalAssessment.Screen.GUIDANCE_REASON
    if not assessment.work_constraints.exists():
        return ProfessionalAssessment.Screen.WORK_CONSTRAINT
    if not assessment.preferred_environment or not assessment.preferred_structure:
        return ProfessionalAssessment.Screen.WORK_STYLE
    if not assessment.domain_category_id:
        return ProfessionalAssessment.Screen.DOMAIN_CATEGORY
    if not assessment.domain_id:
        return ProfessionalAssessment.Screen.DOMAIN
    if not assessment.career_values.exists():
        return ProfessionalAssessment.Screen.CAREER_VALUES
    if not assessment.salary_expectation:
        return ProfessionalAssessment.Screen.SALARY
    if not assessment.timeline:
        return ProfessionalAssessment.Screen.TIMELINE
    if not assessment.platform_goals.exists():
        return ProfessionalAssessment.Screen.PLATFORM_GOALS

    return ProfessionalAssessment.Screen.COMPLETE


def sync_professional_screen(assessment):
    next_screen = calculate_professional_screen(assessment)
    if assessment.current_screen != next_screen:
        assessment.current_screen = next_screen
        assessment.save(update_fields=["current_screen"])
    return assessment


def assessment_status_payload(assessment, user):
    profile = get_professional_profile(user)
    education_level = profile.education_level if profile else None
    stream = profile.stream if profile else None

    if not assessment:
        return {
            "success": True,
            "has_assessment": False,
            "assessment_id": None,
            "is_completed": False,
            "current_screen": ProfessionalAssessment.Screen.CAREER_INTENTION,
            "data": None,
        }

    return {
        "success": True,
        "has_assessment": True,
        "assessment_id": assessment.id,
        "is_completed": assessment.is_completed,
        "current_screen": calculate_professional_screen(assessment),
        "data": {
            "career_intention": assessment.career_intention,
            "education_level": education_level.level_code if education_level else None,
            "stream": stream.stream_code if stream else None,
            "domain_category": (
                str(assessment.domain_category_id)
                if assessment.domain_category_id
                else None
            ),
            "domain": str(assessment.domain_id) if assessment.domain_id else None,
        },
    }


class ProfessionalAssessmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    serializer_class = ProfessionalAssessmentSerializer

    def get_queryset(self):
        return ProfessionalAssessment.objects.filter(
            user=self.request.user,
            deleted=False,
        )

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ProfessionalAssessmentWriteSerializer
        return ProfessionalAssessmentSerializer

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
                sync_professional_screen(assessment)
                serializer = ProfessionalAssessmentSerializer(assessment)
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
            check_token_available(request.user, "assessment")
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        try:
            consume_feature(request.user, "assessment", 1)
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        assessment = ProfessionalAssessment(user=request.user, is_completed=False)
        assessment.save()
        sync_professional_screen(assessment)
        serializer = ProfessionalAssessmentSerializer(assessment)
        return Response(
            {
                "success": True,
                "message": "Assessment created",
                "resume": False,
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        assessment = self.get_object()
        serializer = ProfessionalAssessmentWriteSerializer(
            assessment, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        assessment = serializer.save()
        sync_professional_screen(assessment)
        serializer = ProfessionalAssessmentSerializer(assessment)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="status")
    def assessment_status(self, request):
        assessment = self.get_queryset().order_by("-created_at").first()
        return Response(assessment_status_payload(assessment, request.user))

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        assessment = self.get_object()
        with transaction.atomic():
            assessment.is_completed = True
            assessment.current_screen = ProfessionalAssessment.Screen.COMPLETE
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
                "data": {"id": assessment.id, "is_completed": True},
            },
            status=status.HTTP_200_OK,
        )
