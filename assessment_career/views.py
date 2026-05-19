from django.shortcuts import render
from .serializers import CareerRecommendationSerializer
from rest_framework.viewsets import ModelViewSet
from .models import CareerRecommendation
from rest_framework.filters import SearchFilter, OrderingFilter
from utils.pagination import Pagination
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status

# Create your views here.
class CareerSuggestionViewSet(ModelViewSet):
    serializer_class = CareerRecommendationSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "suggestions__career_name",
    ]
    ordering_fields = [
        "id",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        return (
            CareerRecommendation.objects.filter(deleted=False, user = self.request.user)
            .select_related("assessment","user")
            .prefetch_related("suggestions")
            .order_by("-id")
        )
    
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
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data},status=status.HTTP_200_OK)