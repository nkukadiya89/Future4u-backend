from __future__ import annotations

from typing import Any

from django.db import transaction
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import News
from .permissions import IsAdminUser, IsAuthorOrAdmin
from .serializers import NewsDetailSerializer, NewsListSerializer, NewsSerializer
from .services import NewsService


class StandardResultsSetPagination:
    # Lightweight custom pagination placeholder; projects may replace with global pagination classes
    from rest_framework.pagination import PageNumberPagination

    class P(PageNumberPagination):
        page_size = 10
        page_size_query_param = "page_size"


class NewsViewSet(viewsets.ModelViewSet):
    """ViewSet for news articles.

    Actions:
    - list, retrieve: authenticated
    - create: admin only
    - update/partial_update: author or admin
    - destroy: admin only (soft delete)
    """

    queryset = News.objects.select_related("created_by").all()
    serializer_class = NewsSerializer
    pagination_class = StandardResultsSetPagination.P
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content"]
    ordering_fields = ["published_at", "created_at"]
    ordering = ["-published_at"]

    def get_serializer_class(self) -> Any:
        if self.action == "list":
            return NewsListSerializer
        if self.action in ("retrieve",):
            return NewsDetailSerializer
        return NewsSerializer

    def get_permissions(self) -> list:
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        if self.action == "create":
            return [IsAuthenticated(), IsAdminUser()]
        if self.action in ("update", "partial_update"):
            return [IsAuthenticated(), IsAuthorOrAdmin()]
        if self.action == "destroy":
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(created_by=self.request.user)

    @transaction.atomic
    def perform_destroy(self, instance: News) -> None:
        # Soft delete
        NewsService.soft_delete_news(instance.id)

    def perform_update(self, serializer: Any) -> None:
        # detect publish transition
        instance = serializer.instance
        was_published = bool(getattr(instance, "is_published", False))
        serializer.save()
        instance.refresh_from_db()
        is_published = bool(getattr(instance, "is_published", False))
        if is_published and not was_published:
            NewsService.publish_news(instance.id)
