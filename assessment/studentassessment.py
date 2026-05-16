from domain.models import Domain
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from assessment.models import Option, Question, StudentAssessment, UserResponse
from assessment.serializers import (
    AssessmentResponseSerializer,
    NextQuestionSerializer,
    StudentAssessmentCreateSerializer,
    StudentAssessmentSerializer,
)
from utils.pagination import Pagination
from rest_framework.filters import SearchFilter, OrderingFilter


SIGNAL_ORDER = [
    Question.Dimension.INTEREST,
    Question.Dimension.APTITUDE,
    Question.Dimension.PERSONALITY,
    Question.Dimension.WORK_STYLE,
]

STREAM_REQUIRED_LEVEL_CODES = {
    "secondary",
    "higher_secondary",
    "iti",
    "diploma",
}


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
    from domain.models import Domain

    if not assessment.domain_id:
        return Question.objects.none()

    try:
        domain = Domain.objects.get(id=assessment.domain_id)
    except Domain.DoesNotExist:
        return Question.objects.none()

    # Start with child domain questions
    domain_codes = [domain.domain_code]

    # If category exists, filter questions mapped to BOTH domain AND category
    if assessment.domain_category_id:
        try:
            category = Domain.objects.get(id=assessment.domain_category_id)
            domain_codes = [domain.domain_code, category.domain_code]
        except Domain.DoesNotExist:
            pass

    # Filter by specific dimension if provided
    dimensions = [dimension] if dimension else [
        Question.Dimension.INTEREST,
        Question.Dimension.APTITUDE,
        Question.Dimension.PERSONALITY,
        Question.Dimension.WORK_STYLE,
    ]

    # If both domain and category, question must be mapped to BOTH (AND logic)
    if len(domain_codes) == 2:
        question_pool = Question.objects.filter(
            is_active=True,
            dimension__in=dimensions,
            mapped_domains__domain_code=domain_codes[0],
        ).filter(
            mapped_domains__domain_code=domain_codes[1],
        )
    else:
        question_pool = Question.objects.filter(
            is_active=True,
            mapped_domains__domain_code__in=domain_codes,
            dimension__in=dimensions,
        )

    profile = get_student_profile(user)
    education_level = profile.education_level if profile else None
    if education_level:
        question_pool = question_pool.filter(
            Q(education_level=education_level) | Q(education_level__isnull=True)
        )

    return question_pool.distinct()


def calculate_current_screen(assessment, user):
    if assessment.is_completed:
        return StudentAssessment.Screen.COMPLETE

    profile = get_student_profile(user)
    if not profile or not profile.education_level_id:
        return StudentAssessment.Screen.EDUCATION_LEVEL

    level_code = (profile.education_level.level_code or "").lower()
    if level_code in STREAM_REQUIRED_LEVEL_CODES and not profile.stream_id:
        return StudentAssessment.Screen.STREAM

    if not assessment.domain_category_id:
        return StudentAssessment.Screen.DOMAIN_CATEGORY
    if not assessment.domain_id:
        return StudentAssessment.Screen.DOMAIN
    if not assessment.career_direction:
        return StudentAssessment.Screen.CAREER_DIRECTION
    if not assessment.parent_support:
        return StudentAssessment.Screen.PARENT_SUPPORT
    if not assessment.concerns:
        return StudentAssessment.Screen.CONCERNS

    # Check each dimension in sequence
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
            answered_count = UserResponse.objects.filter(
                assessment=assessment,
                question__in=question_pool,
            ).values("question_id").distinct().count()
            if answered_count < total_questions:
                return screen_name

    if not assessment.career_values:
        return StudentAssessment.Screen.CAREER_VALUES
    if not assessment.user_goals:
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

    sync_current_screen(assessment, user)
    return {
        "success": True,
        "has_assessment": True,
        "assessment_id": assessment.id,
        "is_completed": assessment.is_completed,
        "current_screen": assessment.current_screen,
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
    """
    POST   /api/assessments/start/    
    PATCH  /api/assessments/{id}/      
    POST   /api/assessments/{id}/complete/
    GET    /api/assessments/         
    GET    /api/assessments/{id}/   
    """

    permission_classes = [IsAuthenticated]
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
        "domain_category_name",
        "domain_name",
        "career_direction",
        "parent_support",
        "concerns",
        "career_values",
        "user_goals",
        "is_completed",
    ]
    ordering_fields = [
        "user",
        "domain",
        "career_direction",
        "parent_support",
        "concerns",
        "career_values",
        "user_goals",
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
        """POST /api/assessments/start/ - Resume incomplete assessment or create new."""
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

        assessment = StudentAssessment(
            user=request.user, is_completed=False
        )
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

    @action(detail=False, methods=["get"], url_path="status")
    def assessment_status(self, request):
        """GET /api/student/assessments/status/ - Latest assessment resume state."""
        assessment = self.get_queryset().order_by("-created_at").first()
        return Response(assessment_status_payload(assessment, request.user))

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def complete(self, request, pk=None):
        """POST /api/assessments/{id}/complete/"""
        assessment = self.get_object()
        assessment.is_completed = True
        assessment.current_screen = StudentAssessment.Screen.COMPLETE
        assessment._request_user = request.user
        assessment.updated_by = request.user
        assessment.updated_at = timezone.now()
        assessment.save(update_fields=["is_completed", "current_screen", "updated_at","updated_by"])

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
    """
    GET /api/questions/next/?assessment_id={id}
    Returns the next unanswered question for the given assessment.
    """

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

        # Get already answered questions for this assessment
        answered_ids = (
            UserResponse.objects.filter(assessment=assessment)
            .values_list("question_id", flat=True)
        )

        # Get current screen to determine which dimension questions to show
        current_screen = assessment.current_screen
        
        # Map screen to dimension
        dimension_map = {
            StudentAssessment.Screen.INTEREST: Question.Dimension.INTEREST,
            StudentAssessment.Screen.APTITUDE: Question.Dimension.APTITUDE,
            StudentAssessment.Screen.PERSONALITY: Question.Dimension.PERSONALITY,
            StudentAssessment.Screen.WORK_STYLE: Question.Dimension.WORK_STYLE,
        }
        
        # Get questions for current dimension
        current_dimension = dimension_map.get(current_screen)
        if not current_dimension:
            sync_current_screen(assessment, request.user)
            return Response(
                {
                    "success": True,
                    "message": "No active question dimension",
                    "data": None,
                },
                status=status.HTTP_200_OK,
            )
        
        question_pool = get_question_pool(assessment, request.user, current_dimension)
        total_questions = question_pool.count()
        
        # Get answered questions for this dimension
        answered_ids = (
            UserResponse.objects.filter(
                assessment=assessment,
                question__in=question_pool
            )
            .values_list("question_id", flat=True)
        )
        answered_count = len(answered_ids)
        
        qs = question_pool.exclude(id__in=answered_ids)
        next_q = qs.order_by("sequence_order").first()

        if not next_q:
            sync_current_screen(assessment, request.user)
            message = (
                "No questions found for selected domain"
                if total_questions == 0
                else "All questions completed for selected domains"
            )
            return Response(
                {
                    "success": True,
                    "message": message,
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
    """
    POST /api/responses/
    Body: { "assessment": 101, "question": 1, "selected_option": 11 }
    Saves a single answer and returns the option's score.
    """

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
        option_id = ser.validated_data["selected_option"]

        # Validate assessment belongs to user
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

        # Validate question and option
        try:
            question = Question.objects.get(id=question_id, is_active=True)
            option = Option.objects.get(id=option_id, question=question)
        except Question.DoesNotExist:
            return Response(
                {"success": False, "message": "Invalid question"},
                status=status.HTTP_404_NOT_FOUND,
            )   
        except Option.DoesNotExist:
            return Response(
                {"success": False, "message": "Invalid option for this question"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Enforce: one answer per question per assessment
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
