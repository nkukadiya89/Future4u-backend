from __future__ import annotations

from typing import Any, Dict, Iterable, List

from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Notification


class NotificationService:
    """Service layer for user notifications."""

    @staticmethod
    def create_notification(user: Any, notification_type: str, title: str, message: str, metadata: Dict[str, Any] | None = None) -> Notification:
        metadata = metadata or {}
        return Notification.objects.create(
            user=user, notification_type=notification_type, title=title, message=message, metadata=metadata
        )

    @staticmethod
    def bulk_create_notifications(items: Iterable[Dict[str, Any]]) -> List[Notification]:
        """Bulk create notification dictionaries.

        items: iterable of dicts with keys (user, notification_type, title, message, metadata)
        """

        objs = [Notification(**item) for item in items]
        with transaction.atomic():
            created = Notification.objects.bulk_create(objs)
        return created

    @staticmethod
    def mark_read(notification_id: Any, user: Any) -> Notification:
        notification = get_object_or_404(Notification, pk=notification_id, user=user)
        notification.mark_read()
        return notification

    @staticmethod
    def mark_all_read(user: Any) -> int:
        with transaction.atomic():
            updated = Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        return updated

    @staticmethod
    def delete_notification(notification_id: Any, user: Any) -> None:
        notification = get_object_or_404(Notification, pk=notification_id, user=user)
        notification.delete()
