from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.master_view import BaseModelViewSet
from utils.pagination import Pagination
from utils.token_check import check_token_available

from .models import (
    CareerRecommendation,
    CareerSuggestion,
)
from .serializers import (
    CareerRecommendationSerializer,
    CareerSuggestionSerializer,
)


class CareerSuggestionViewSet(ModelViewSet):
    serializer_class = CareerRecommendationSerializer
    profile_type = None
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    ordering_fields = [
        "id",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        queryset = (
            CareerRecommendation.objects.filter(
                deleted=False,
                user=self.request.user,
            )
            .select_related(
                "student_assessment",
                "parent_assessment",
                "professional_assessment",
                "user",
            )
            .prefetch_related("suggestions")
            .order_by("-id")
        )
        if self.profile_type:
            queryset = queryset.filter(profile_type=self.profile_type)
        assessment_id = self.request.query_params.get("assessment_id")
        if assessment_id:
            if self.profile_type == CareerRecommendation.ProfileType.STUDENT:
                queryset = queryset.filter(student_assessment_id=assessment_id)
            elif self.profile_type == CareerRecommendation.ProfileType.PARENT:
                queryset = queryset.filter(parent_assessment_id=assessment_id)
            elif self.profile_type == CareerRecommendation.ProfileType.PROFESSIONAL:
                queryset = queryset.filter(professional_assessment_id=assessment_id)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = CareerRecommendationSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response(
                {
                    "success": False,
                    "message": "No recommendation matches the given query",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.serializer_class(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="compare")
    def compare(self, request):
        try:
            check_token_available(request.user, "career_compare")
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        suggestion_ids = request.query_params.get("suggestion_ids")

        if not suggestion_ids:
            return Response(
                {"success": False, "message": "Suggestion ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suggestion_ids = [
            item.strip() for item in suggestion_ids.split(",") if item.strip()
        ]
        if len(suggestion_ids) != 2:
            return Response(
                {
                    "success": False,
                    "message": "Please provide exactly 2 suggestion ids",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            suggestion_ids = [int(item) for item in suggestion_ids]
        except ValueError:
            return Response(
                {
                    "success": False,
                    "message": "Suggestion ids must be valid numbers",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        suggestions = CareerSuggestion.objects.filter(
            id__in=suggestion_ids,
            recommendation__user=request.user,
            deleted=False,
        ).order_by("display_order")
        if self.profile_type:
            suggestions = suggestions.filter(
                recommendation__profile_type=self.profile_type
            )

        if suggestions.count() != 2:
            return Response(
                {"success": False, "message": "Invalid suggestion ids"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recommendation_ids = {
            suggestion.recommendation_id for suggestion in suggestions
        }
        if len(recommendation_ids) != 1:
            return Response(
                {
                    "success": False,
                    "message": "Please compare suggestions from the same recommendation",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CareerSuggestionSerializer(suggestions, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class CareerSuggestionDetailViewSet(BaseModelViewSet):
    serializer_class = CareerSuggestionSerializer
    profile_type = None
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CareerSuggestion.objects.filter(
            deleted=False,
            recommendation__user=self.request.user,
        )
        if self.profile_type:
            queryset = queryset.filter(recommendation__profile_type=self.profile_type)
        return queryset


class StudentCareerSuggestionViewSet(CareerSuggestionViewSet):
    profile_type = CareerRecommendation.ProfileType.STUDENT


class StudentCareerSuggestionDetailViewSet(CareerSuggestionDetailViewSet):
    profile_type = CareerRecommendation.ProfileType.STUDENT


class ParentCareerSuggestionViewSet(CareerSuggestionViewSet):
    profile_type = CareerRecommendation.ProfileType.PARENT


class ParentCareerSuggestionDetailViewSet(CareerSuggestionDetailViewSet):
    profile_type = CareerRecommendation.ProfileType.PARENT


class ProfessionalCareerSuggestionViewSet(CareerSuggestionViewSet):
    profile_type = CareerRecommendation.ProfileType.PROFESSIONAL


class ProfessionalCareerSuggestionDetailViewSet(CareerSuggestionDetailViewSet):
    profile_type = CareerRecommendation.ProfileType.PROFESSIONAL
