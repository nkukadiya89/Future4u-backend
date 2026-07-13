from __future__ import annotations

from typing import Any

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .permissions import IsNotificationOwner
from .serializers import NotificationListSerializer, NotificationSerializer
from .services import NotificationService


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """ViewSet for user notifications."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Always filter by the requesting user
        return Notification.objects.filter(user=self.request.user).order_by("is_read", "-created_at")

    def get_serializer_class(self) -> Any:
        if self.action == "list":
            return NotificationListSerializer
        return NotificationSerializer

    @action(methods=["POST"], detail=True, url_path="mark_read")
    def mark_read(self, request: Any, pk: str = None) -> Response:
        NotificationService.mark_read(pk, request.user)
        return Response(status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, url_path="mark_all_read")
    def mark_all_read(self, request: Any) -> Response:
        updated = NotificationService.mark_all_read(request.user)
        return Response({"updated": updated}, status=status.HTTP_200_OK)
