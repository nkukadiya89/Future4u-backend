from __future__ import annotations

from typing import Any, Dict, Optional

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "metadata",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class NotificationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "notification_type", "title", "message", "is_read", "created_at"]
