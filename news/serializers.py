from __future__ import annotations

from typing import Any, Dict, Optional

from rest_framework import serializers

from .models import News


class NewsSerializer(serializers.ModelSerializer):
    """Serializer used for create/update operations."""

    class Meta:
        model = News
        fields = [
            "id",
            "title",
            "short_description",
            "content",
            "category",
            "image",
            "is_published",
            "published_at",
        ]
        read_only_fields = ["id", "published_at"]


class NewsListSerializer(serializers.ModelSerializer):
    """Compact representation for lists."""

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = News
        fields = [
            "id",
            "title",
            "short_description",
            "category",
            "image_url",
            "published_at",
        ]

    def get_image_url(self, obj: News) -> Optional[str]:
        request = self.context.get("request")
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class NewsDetailSerializer(serializers.ModelSerializer):
    """Detailed representation for single object views."""

    image_url = serializers.SerializerMethodField()
    highlights = serializers.SerializerMethodField()

    class Meta:
        model = News
        fields = [
            "id",
            "title",
            "category",
            "image_url",
            "published_at",
            "content",
            "highlights",
        ]

    def get_image_url(self, obj: News) -> Optional[str]:
        request = self.context.get("request")
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def get_highlights(self, obj: News) -> Optional[Dict[str, Any]]:
        """Create an optional highlights summary. Keeps things lightweight for UI."""

        # Simple heuristic: first 200 chars as summary and first line as heading
        if not obj.content:
            return None
        summary = obj.content.strip()[:200]
        first_line = obj.content.strip().split("\n", 1)[0]
        return {"heading": first_line[:120], "summary": summary}
