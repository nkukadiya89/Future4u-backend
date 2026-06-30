from __future__ import annotations

from typing import List

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404

from notifications.models import Notification

from .models import News


@shared_task(bind=True)
def notify_users_about_news(self, news_id: str) -> None:
    """Create notifications for users when a news article is published.

    This uses bulk_create for efficiency and excludes the article author.
    """

    news = get_object_or_404(News.all_objects, pk=news_id)
    User = get_user_model()
    queryset = User.objects.filter(is_active=True).exclude(pk=news.created_by_id)

    batch: List[Notification] = []
    now = None
    for user in queryset.iterator():
        batch.append(
            Notification(
                user=user,
                notification_type="news",
                title="New News Published",
                message=f"A new news article '{news.title}' is available.",
                metadata={"news_id": str(news.id)},
            )
        )

    # Bulk insert in a transaction
    if batch:
        with transaction.atomic():
            Notification.objects.bulk_create(batch)
