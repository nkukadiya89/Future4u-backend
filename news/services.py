from __future__ import annotations

from typing import Any, Dict, Optional

from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import News


class NewsService:
    """Service layer for news operations."""

    @staticmethod
    @transaction.atomic
    def create_news(user: Any, validated_data: Dict[str, Any]) -> News:
        """Create a news article associated with `user`."""

        news = News.objects.create(created_by=user, **validated_data)
        return news

    @staticmethod
    @transaction.atomic
    def update_news(news_id: Any, validated_data: Dict[str, Any]) -> News:
        """Update a news article by id."""

        news = get_object_or_404(News.all_objects, pk=news_id)
        for attr, value in validated_data.items():
            setattr(news, attr, value)
        news.save()
        return news

    @staticmethod
    @transaction.atomic
    def publish_news(news_id: Any) -> News:
        """Mark a news article as published and trigger notifications via Celery."""

        news = get_object_or_404(News.all_objects, pk=news_id)
        if not news.is_published:
            news.publish()
            # Trigger async notifications
            try:
                from .tasks import notify_users_about_news

                notify_users_about_news.delay(str(news.id))
            except Exception:
                # Fail silently here; the task system should report errors.
                pass
        return news

    @staticmethod
    @transaction.atomic
    def soft_delete_news(news_id: Any) -> None:
        """Soft-delete a news article."""

        news = get_object_or_404(News.all_objects, pk=news_id)
        news.soft_delete()
