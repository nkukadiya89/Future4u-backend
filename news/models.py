from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone


class NewsManager(models.Manager):
    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().filter(is_deleted=False)


class News(models.Model):
    """News article model with soft-delete and publication metadata."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    short_description = models.CharField(max_length=512, blank=True)
    content = models.TextField()
    category = models.CharField(max_length=100, db_index=True)
    image = models.ImageField(upload_to="news/images/", null=True, blank=True)
    is_published = models.BooleanField(default=False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="news_articles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = NewsManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["-published_at"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_published"]),
        ]

    def publish(self, when: Any = None) -> None:
        """Mark the article published and set published timestamp."""

        if when is None:
            when = timezone.now()
        self.is_published = True
        self.published_at = when
        self.save(update_fields=["is_published", "published_at", "updated_at"])

    def soft_delete(self) -> None:
        """Soft delete the article."""

        self.is_deleted = True
        # Optionally unpublish on delete
        self.is_published = False
        self.save(update_fields=["is_deleted", "is_published", "updated_at"])

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title
