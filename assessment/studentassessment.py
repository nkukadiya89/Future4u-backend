from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from assessment.models import Option, Question, StudentAssessment, UserResponse
from assessment.serializers import (
    AssessmentResponseSerializer,
    NextQuestionSerializer,
    StudentAssessmentCreateSerializer,
    StudentAssessmentSerializer,
)
from utils.pagination import Pagination
from rest_framework.filters import SearchFilter, OrderingFilter

class StudentAssessmentViewSet(viewsets.ModelViewSet):
    """
    POST   /api/assessments/start/     -> Create new assessment session
    PATCH  /api/assessments/{id}/      -> Update form fields (step 2-5, 9-10)
    POST   /api/assessments/{id}/complete/ -> Finalize assessment
    GET    /api/assessments/           -> List user's assessments
    GET    /api/assessments/{id}/      -> Retrieve single assessment
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    serializer_class = StudentAssessmentSerializer
    
    def get_queryset(self):
        return StudentAssessment.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return StudentAssessmentCreateSerializer
        return StudentAssessmentSerializer
    
    search_fields = [
        "id",
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
        """POST /api/assessments/start/ - Always creates a new assessment"""
        assessment = StudentAssessment.objects.create(
            user=request.user, is_completed=False
        )
        serializer = StudentAssessmentCreateSerializer(assessment)
        return Response(
            {
                "success": True,
                "message": "Assessment created",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def complete(self, request, pk=None):
        """POST /api/assessments/{id}/complete/"""
        assessment = self.get_object()
        assessment.is_completed = True
        assessment.save()

        return Response(
            {
                "success": True,
                "message": "Assessment completed",
                "data": {
                    "id": assessment.id,
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
                id=assessment_id, user=request.user
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

        # Use broad category questions plus selected child-domain questions.
        domain_ids = [
            domain_id
            for domain_id in (
                assessment.domain_category_id,
                assessment.domain_id,
            )
            if domain_id
        ]

        # Build base queryset
        qs = Question.objects.filter(
            is_active=True,
            mapped_domains__id__in=domain_ids,
        ).exclude(id__in=answered_ids)

        # Progressive dimensions: interest -> aptitude -> personality -> work_style
        DIMENSION_ORDER = [
            Question.Dimension.INTEREST,
            Question.Dimension.APTITUDE,
            Question.Dimension.PERSONALITY,
            Question.Dimension.WORK_STYLE,
        ]

        next_q = None
        for dim in DIMENSION_ORDER:
            candidate = qs.filter(dimension=dim).order_by("sequence_order").first()
            if candidate:
                next_q = candidate
                break

        if not next_q:
            return Response(
                {
                    "success": True,
                    "message": "All questions completed for selected domains",
                    "data": None,
                },
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(next_q)
        return Response(
            {"success": True, "data": serializer.data},
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
                id=assessment_id, user=request.user
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
                "score_value": option.score_value,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Response saved",
                "data": {"score": option.score_value},
            },
            status=status.HTTP_200_OK,
        )
