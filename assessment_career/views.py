from django.db.models import Prefetch
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.pagination import Pagination

from .models import CareerRecommendation, CareerRecommendationSuggestion
from .serializers import (
    CareerRecommendationDetailSerializer,
    CareerRecommendationSerializer,
    CareerRecommendationSuggestionSerializer,
)
from rest_framework.viewsets import ModelViewSet
from .models import CareerRecommendation, CareerRecommendationSuggestion
from rest_framework.filters import SearchFilter, OrderingFilter
from utils.pagination import Pagination
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from common.master_view import BaseModelViewSet


class CareerSuggestionViewSet(ModelViewSet):
    serializer_class = CareerRecommendationSerializer
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
        queryset = CareerRecommendation.objects.filter(deleted=False, user=self.request.user).select_related("assessment", "user").prefetch_related("suggestions").order_by("-id")
        assessment_id = self.request.query_params.get("assessment_id")
        if assessment_id:
            queryset = queryset.filter(assessment_id=assessment_id)
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
            return Response({"success":False, "message":"No CareerRecommendation matches the given query"},status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="compare")
    def compare(self, request):
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

        suggestions = CareerRecommendationSuggestion.objects.filter(
            id__in = suggestion_ids, recommendation__user=request.user, deleted=False
        ).order_by("display_order")

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

        serializer = CareerRecommendationSuggestionSerializer(suggestions, many=True)
        return Response({"success":True, "data":serializer.data}, status=status.HTTP_200_OK)
    
class CareerSuggestionDetailViewSet(BaseModelViewSet):
    serializer_class = CareerRecommendationSuggestionSerializer
    
    def get_queryset(self):
        return CareerRecommendationSuggestion.objects.filter(
            deleted=False,
            recommendation__user=self.request.user
        )
