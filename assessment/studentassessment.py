from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from assessment.models import (
    CareerDirection,
    CareerValue,
    Concern,
    Option,
    Question,
    StudentAssessment,
    UserGoal,
    UserResponse,
)
from assessment.serializers import (
    AssessmentResponseSerializer,
    CareerDirectionSerializer,
    CareerValueSerializer,
    ConcernSerializer,
    NextQuestionSerializer,
    StudentAssessmentCreateSerializer,
    StudentAssessmentSerializer,
    UserGoalSerializer,
)
from common.api.mixins import ArchiveMixin
from common.master_view import BaseModelViewSet
from domain.models import Domain
from subscription.services.usage import consume_feature
from user.permissions import IsIndividualUser
from utils.pagination import Pagination
from utils.token_check import check_token_available

STREAM_REQUIRED_LEVEL_CODES = {
    "higher_secondary_11",
    "higher_secondary",
    "iti",
    "diploma",
}

QUESTION_DIMENSIONS = [
    Question.Dimension.INTEREST,
    Question.Dimension.APTITUDE,
    Question.Dimension.PERSONALITY,
    Question.Dimension.WORK_STYLE,
]

QUESTIONS_PER_DIMENSION = 3


def get_student_profile(user):
    try:
        from user_profile.models import StudentProfile

        return StudentProfile.objects.select_related(
            "education_level",
            "stream",
        ).get(user=user)
    except StudentProfile.DoesNotExist:
        return None


def get_question_pool(assessment, user, dimension=None):
    if not assessment.domain_id:
        return Question.objects.none()

    try:
        domain = Domain.objects.get(id=assessment.domain_id)
    except Domain.DoesNotExist:
        return Question.objects.none()

    dimensions = [dimension] if dimension else QUESTION_DIMENSIONS

    base_pool = Question.objects.filter(is_active=True, dimension__in=dimensions)

    profile = get_student_profile(user)
    education_level = profile.education_level if profile else None
    if education_level:
        base_pool = base_pool.filter(
            Q(education_level=education_level) | Q(education_level__isnull=True)
        )
    else:
        base_pool = base_pool.filter(education_level__isnull=True)

    stream = profile.stream if profile else None
    if stream:
        base_pool = base_pool.filter(
            Q(target_stream=stream) | Q(target_stream__isnull=True)
        )
    else:
        base_pool = base_pool.filter(target_stream__isnull=True)

    question_pool = base_pool.filter(mapped_domains__domain_code=domain.domain_code)

    # Product rule: selected child domain is the main source. Parent/category
    # questions are only a fallback when that child has no questions.
    if not question_pool.exists() and assessment.domain_category_id:
        try:
            category = Domain.objects.get(id=assessment.domain_category_id)
            question_pool = base_pool.filter(
                mapped_domains__domain_code=category.domain_code
            )
        except Domain.DoesNotExist:
            pass

    ordered_pool = question_pool.distinct().order_by(
        "-signal_strength",
        "sequence_order",
        "id",
    )
    if dimension:
        ids = list(ordered_pool.values_list("id", flat=True)[:QUESTIONS_PER_DIMENSION])
        return Question.objects.filter(id__in=ids).order_by("sequence_order", "id")

    ids = []
    for dim in QUESTION_DIMENSIONS:
        ids.extend(
            ordered_pool.filter(dimension=dim).values_list("id", flat=True)[
                :QUESTIONS_PER_DIMENSION
            ]
        )
    return Question.objects.filter(id__in=ids).order_by(
        "dimension", "sequence_order", "id"
    )


def calculate_current_screen(assessment, user):
    if assessment.is_completed:
        return StudentAssessment.Screen.COMPLETE

    profile = get_student_profile(user)
    if not profile or not profile.education_level_id:  # type: ignore
        return StudentAssessment.Screen.EDUCATION_LEVEL

    level_code = (profile.education_level.level_code or "").lower()  # type: ignore
    if level_code in STREAM_REQUIRED_LEVEL_CODES and not profile.stream_id:  # type: ignore
        return StudentAssessment.Screen.STREAM

    if not assessment.domain_category_id:
        return StudentAssessment.Screen.DOMAIN_CATEGORY
    if not assessment.domain_id:
        return StudentAssessment.Screen.DOMAIN
    if not assessment.career_direction.exists():
        return StudentAssessment.Screen.CAREER_DIRECTION
    if not assessment.parent_support:
        return StudentAssessment.Screen.PARENT_SUPPORT
    if not assessment.concerns.exists():
        return StudentAssessment.Screen.CONCERNS

    dimensions = [
        (Question.Dimension.INTEREST, StudentAssessment.Screen.INTEREST),
        (Question.Dimension.APTITUDE, StudentAssessment.Screen.APTITUDE),
        (Question.Dimension.PERSONALITY, StudentAssessment.Screen.PERSONALITY),
        (Question.Dimension.WORK_STYLE, StudentAssessment.Screen.WORK_STYLE),
    ]

    for dimension, screen_name in dimensions:
        question_pool = get_question_pool(assessment, user, dimension)
        total_questions = question_pool.count()
        if total_questions:
            answered_count = (
                UserResponse.objects.filter(
                    assessment=assessment,
                    question__in=question_pool,
                )
                .values("question_id")
                .distinct()
                .count()
            )
            if answered_count < total_questions:
                return screen_name

    if not assessment.career_values.exists():
        return StudentAssessment.Screen.CAREER_VALUES
    if not assessment.user_goals.exists():
        return StudentAssessment.Screen.USER_GOALS

    return StudentAssessment.Screen.COMPLETE


def sync_current_screen(assessment, user):
    next_screen = calculate_current_screen(assessment, user)
    if assessment.current_screen != next_screen:
        assessment.current_screen = next_screen
        assessment.save(update_fields=["current_screen"])
    return assessment


def assessment_status_payload(assessment, user):
    profile = get_student_profile(user)
    education_level = profile.education_level if profile else None
    stream = profile.stream if profile else None

    if not assessment:
        return {
            "success": True,
            "has_assessment": False,
            "assessment_id": None,
            "is_completed": False,
            "current_screen": StudentAssessment.Screen.EDUCATION_LEVEL,
            "data": None,
        }

    return {
        "success": True,
        "has_assessment": True,
        "assessment_id": assessment.id,
        "is_completed": assessment.is_completed,
        "current_screen": calculate_current_screen(assessment, user),
        "data": {
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


class StudentAssessmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsIndividualUser]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    serializer_class = StudentAssessmentSerializer

    def get_queryset(self):
        return StudentAssessment.objects.filter(
            user=self.request.user,
            deleted=False,
        )

    def get_serializer_class(self):
        if self.action == "create":
            return StudentAssessmentCreateSerializer
        return StudentAssessmentSerializer

    search_fields = [
        "id",
        "parent_support",
        "concerns__name",
        "career_values__name",
        "user_goals__name",
        "domain_category__domain_name",
        "domain__domain_name",
        "career_direction__name",
        "is_completed",
    ]
    ordering_fields = [
        "user",
        "domain",
        "parent_support",
        "concerns",
        "career_values",
        "user_goals",
        "career_direction",
        "created_at",
        "updated_at",
        "is_completed",
    ]

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
                sync_current_screen(assessment, request.user)
                serializer = StudentAssessmentCreateSerializer(assessment)
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

        assessment = StudentAssessment(user=request.user, is_completed=False)
        assessment._request_user = request.user
        assessment.save()
        sync_current_screen(assessment, request.user)
        serializer = StudentAssessmentCreateSerializer(assessment)
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
        sync_current_screen(assessment, self.request.user)
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
        return Response(assessment_status_payload(assessment, request.user))

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """POST /api/assessments/{id}/complete/"""
        assessment = self.get_object()
        with transaction.atomic():
            assessment.is_completed = True
            assessment.current_screen = StudentAssessment.Screen.COMPLETE
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


class NextQuestionViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = NextQuestionSerializer
    pagination_class = Pagination

    def list(self, request):
        assessment_id = request.query_params.get("assessment_id")
        if not assessment_id:
            return Response(
                {
                    "success": False,
                    "message": "assessment_id query parameter is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            assessment = StudentAssessment.objects.get(
                id=assessment_id,
                user=request.user,
                deleted=False,
            )
        except StudentAssessment.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Invalid assessment_id or access denied",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        current_screen = calculate_current_screen(assessment, request.user)

        dimension_map = {
            StudentAssessment.Screen.INTEREST: Question.Dimension.INTEREST,
            StudentAssessment.Screen.APTITUDE: Question.Dimension.APTITUDE,
            StudentAssessment.Screen.PERSONALITY: Question.Dimension.PERSONALITY,
            StudentAssessment.Screen.WORK_STYLE: Question.Dimension.WORK_STYLE,
        }

        # Get questions for current dimension
        current_dimension = dimension_map.get(current_screen)
        if not current_dimension:
            is_assessment_complete = current_screen == StudentAssessment.Screen.COMPLETE
            return Response(
                {
                    "success": True,
                    "message": (
                        "Assessment completed"
                        if is_assessment_complete
                        else "Assessment is not currently on a question screen"
                    ),
                    "current_screen": current_screen,
                    "data": None,
                },
                status=status.HTTP_200_OK,
            )

        question_pool = get_question_pool(assessment, request.user, current_dimension)
        total_questions = question_pool.count()

        # Get answered questions for this dimension
        answered_ids = UserResponse.objects.filter(
            assessment=assessment, question__in=question_pool
        ).values_list("question_id", flat=True)
        answered_count = len(answered_ids)

        qs = question_pool.exclude(id__in=answered_ids)
        next_q = qs.order_by("-signal_strength", "sequence_order").first()

        if not next_q:
            message = (
                "No questions found for selected domain"
                if total_questions == 0
                else "All questions completed for current section"
            )
            return Response(
                {
                    "success": True,
                    "message": message,
                    "current_screen": current_screen,
                    "data": None,
                    "progress": {
                        "question_number": total_questions,
                        "total_questions": total_questions,
                        "answered": total_questions,
                        "remaining": 0,
                        "is_complete": True,
                    },
                },
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(next_q)
        return Response(
            {
                "success": True,
                "data": serializer.data,
                "progress": {
                    "question_number": answered_count + 1,
                    "total_questions": total_questions,
                    "answered": answered_count,
                    "remaining": max(total_questions - answered_count, 0),
                    "is_complete": False,
                },
            },
            status=status.HTTP_200_OK,
        )


class AssessmentResponseViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = AssessmentResponseSerializer

    @transaction.atomic
    def create(self, request):
        ser = self.get_serializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assessment_id = ser.validated_data["assessment"]
        question_id = ser.validated_data["question"]

        try:
            assessment = StudentAssessment.objects.get(
                id=assessment_id,
                user=request.user,
                deleted=False,
            )
        except StudentAssessment.DoesNotExist:
            return Response(
                {"success": False, "message": "Invalid assessment_id"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if assessment.is_completed:
            return Response(
                {"success": False, "message": "Assessment already completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sync_current_screen(assessment, request.user)
        dimension_map = {
            StudentAssessment.Screen.INTEREST: Question.Dimension.INTEREST,
            StudentAssessment.Screen.APTITUDE: Question.Dimension.APTITUDE,
            StudentAssessment.Screen.PERSONALITY: Question.Dimension.PERSONALITY,
            StudentAssessment.Screen.WORK_STYLE: Question.Dimension.WORK_STYLE,
        }
        current_dimension = dimension_map.get(assessment.current_screen)
        if not current_dimension:
            return Response(
                {
                    "success": False,
                    "message": "Assessment is not currently on a question screen",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        question = (
            get_question_pool(assessment, request.user, current_dimension)
            .filter(id=question_id)
            .first()
        )
        if not question:
            return Response(
                {
                    "success": False,
                    "message": "Invalid question for current assessment step",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        option_id = ser.validated_data.get("selected_option")
        if not option_id:
            return Response(
                {
                    "success": False,
                    "message": "selected_option is required for this question",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            option = Option.objects.get(id=option_id, question=question)
        except Option.DoesNotExist:
            return Response(
                {"success": False, "message": "Invalid option for this question"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        UserResponse.objects.update_or_create(
            assessment=assessment,
            user=request.user,
            question=question,
            defaults={
                "selected_option": option,
            },
        )

        sync_current_screen(assessment, request.user)

        return Response(
            {
                "success": True,
                "message": "Response saved",
                "data": {
                    "current_screen": assessment.current_screen,
                },
            },
            status=status.HTTP_200_OK,
        )


class ConcernViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = Concern.objects.all().order_by("-id")
    serializer_class = ConcernSerializer

    search_fields = BaseModelViewSet.searching_fields + ["name"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["name"]


class CareerValueViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = CareerValue.objects.all().order_by("-id")
    serializer_class = CareerValueSerializer

    search_fields = BaseModelViewSet.searching_fields + ["name"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["name"]


class UserGoalViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = UserGoal.objects.all().order_by("-id")
    serializer_class = UserGoalSerializer

    search_fields = BaseModelViewSet.searching_fields + ["name"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["name"]


class CareerDirectionViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = CareerDirection.objects.all().order_by("-id")
    serializer_class = CareerDirectionSerializer

    search_fields = BaseModelViewSet.searching_fields + ["name"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["name"]
