from common.master_view import BaseModelViewSet
from .student_organization_serializers import OrganizationStudentCreateSerializer, OrganizationStudentListSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.parsers import FormParser, MultiPartParser
from user.models import User
from utils.pagination import Pagination
from .permissions import IsSchoolCollegeOrInstitute
from django.db import transaction
from django.db.models import Q
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from django.utils import timezone
from assessment.models import StudentAssessment
from assessment.serializers import StudentAssessmentSerializer
from assessment_career.models import CareerRecommendation, CareerSuggestion
from assessment_career.serializers import CareerRecommendationSerializer, CareerSuggestionSerializer

class OrganizationStudentViewSet(BaseModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsSchoolCollegeOrInstitute]
    pagination_class = Pagination
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = BaseModelViewSet.searching_fields +[
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

    ordering_fields = BaseModelViewSet.ordering_fields +[
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
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        return User.objects.filter(
            Q(created_by=user) | Q(student_profile__referred_by=user),
            user_type=User.Role.STUDENT,
            deleted=False,
        ).select_related(
            "country",
            "states",
            "city",
            "student_profile",
            "student_profile__education_level",
        ).prefetch_related(
            "student_assessments",
            "career_recommendations",
            "career_recommendations__suggestions",
        ).order_by("-id")
    
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
        serializer = self.get_serializer(data=request.data, context={"request": request})
        if serializer.is_valid(raise_exception=True):
            student = serializer.save()
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
            return Response({"success": True, "data": serializer.data},status=status.HTTP_200_OK)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data},status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        student = self.get_object()
        serializer = self.get_serializer(student)
        return Response(
            {
                "success" : True,
                "data" : serializer.data,
            },
            status=status.HTTP_200_OK
        )    
    

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        student = (
            User.objects.filter(pk=kwargs.get("pk"), deleted=False, user_type=User.Role.STUDENT).first()
        )

        if student.created_by_id != request.user.id:
            return Response(
                {
                    "success" : False,
                    "message" : "You can archive students created by you",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if student.deleted:
            return Response(
                {
                    "success" : False,
                    "message" : "Student alredy archived",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if student.status == "active":
            return Response(
                {
                    "success" : False,
                    "message" : "Active student can not archive. Please inactive this student first.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        student.deleted = True
        student.deleted_at = timezone.now()
        student.deleted_by = request.user
        student.save(update_fields=["deleted", "deleted_at", "deleted_by"])
        return Response(
            {
                "success": True,
                "message": "Student archived successfully",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="assessments")
    def student_assessment(self, request, pk=None):
        student = self.get_object()
        queryset = StudentAssessment.objects.filter(user=student, deleted=False).order_by("-created_at")
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success" : True,
                    "data" : serializer.data,
                },
                status= status.HTTP_200_OK,
            )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {
                    "success" : True,
                    "data" : serializer.data,
                },
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response(
            {
                "success" : True,
                "data" : serializer.data,
            },
        )
    @action(detail=True, methods=["get"], url_path="recommendation")
    def student_recommendation(self, request, pk=None):
        assessment_id = request.query_params.get("assessment_id")
        if not assessment_id:
            return Response(
                {
                    "success" : False,
                    "message" : "Assessment id is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        student = self.get_object()
        assessment = StudentAssessment.objects.filter(id=assessment_id, user=student, deleted=False).first()
        if not assessment:
            return Response(
                {
                    "success" : False,
                    "message" : "Assessment not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        recommendation = (CareerRecommendation.objects.filter(student_assessment=assessment, deleted=False).prefetch_related("suggestions").first())
        if not recommendation:
            return Response(
                {
                    "success" : False,
                    "message" : "Recommendation not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = CareerRecommendationSerializer(recommendation)
        return Response(
            {
                "success" : True,
                "data" : serializer.data,
            },
            status=status.HTTP_200_OK,
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
        suggestion = CareerSuggestion.objects.filter(
            id=suggestion_id,
            deleted=False,  
            recommendation__user=student,
            recommendation__profile_type="student",
        ).select_related("recommendation").first()
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
