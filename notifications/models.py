from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """Per-user notification record."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=80, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["is_read", "-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def mark_read(self) -> None:
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=["is_read", "updated_at"])

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Notification to {self.user_id}: {self.title}"
