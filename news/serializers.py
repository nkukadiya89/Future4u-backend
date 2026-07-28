from __future__ import annotations

from typing import Any, Dict, Optional

from rest_framework import serializers

from .models import News


class NewsSerializer(serializers.ModelSerializer):
    """Serializer used for create/update operations."""

    image_file = serializers.ImageField(
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = News
        fields = [
            "id",
            "title",
            "short_description",
            "content",
            "category",
            "image",
            "image_file",
            "is_published",
            "published_at",
        ]
        read_only_fields = ["id", "published_at", "image"]

    def validate(self, attrs):
        attrs["image_file"] = self.context["request"].FILES.get("image")
        return attrs

    def create(self, validated_data):
        image_file = validated_data.pop("image_file", None)
        news = News.objects.create(**validated_data)

        if image_file:
            news.upload_news_image(image_file)
            news.refresh_from_db(fields=["image"])

        return news

    def update(self, instance, validated_data):
        image_file = validated_data.pop("image_file", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if image_file:
            instance.upload_news_image(image_file)
            instance.refresh_from_db(fields=["image"])

        instance.save()
        return instance


class NewsListSerializer(serializers.ModelSerializer):
    """Compact representation for lists."""

    image_url = serializers.CharField(source="image", allow_null=True)

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


class NewsDetailSerializer(serializers.ModelSerializer):
    """Detailed representation for single object views."""

    image_url = serializers.CharField(source="image", allow_null=True)
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

    def get_highlights(self, obj: News) -> Optional[Dict[str, Any]]:
        """Create an optional highlights summary. Keeps things lightweight for UI."""

        # Simple heuristic: first 200 chars as summary and first line as heading
        if not obj.content:
            return None
        summary = obj.content.strip()[:200]
        first_line = obj.content.strip().split("\n", 1)[0]
        return {"heading": first_line[:120], "summary": summary}
