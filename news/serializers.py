from __future__ import annotations

from typing import Any, Dict, Optional

from rest_framework import serializers

from .models import News


class NewsSerializer(serializers.ModelSerializer):
    """Serializer used for create/update operations."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Override image field to return S3 URL directly
        if instance.image and instance.image.name:
            if instance.image.name.startswith("http"):
                data["image"] = instance.image.name
            else:
                request = self.context.get("request")
                if request:
                    data["image"] = request.build_absolute_uri(instance.image.url)
                else:
                    data["image"] = instance.image.url
        return data

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
        read_only_fields = ["id"]

    def create(self, validated_data):
        image_file = validated_data.pop("image", None)

        # Auto-set published_at if is_published is True
        if validated_data.get("is_published") and not validated_data.get(
            "published_at"
        ):
            from django.utils import timezone

            validated_data["published_at"] = timezone.now()

        news = News.objects.create(**validated_data)

        # Upload image to S3 if provided
        if image_file:
            try:
                s3_url = news.upload_image_to_s3(image_file)
                news.image.name = s3_url  # Store S3 URL in ImageField
                news.save(update_fields=["image"])
            except Exception as e:
                raise serializers.ValidationError({"image": str(e)})

        return news

    def update(self, instance, validated_data):
        image_file = validated_data.pop("image", None)

        # Auto-set published_at if is_published is changed to True and published_at is None
        if validated_data.get("is_published") and not instance.published_at:
            from django.utils import timezone

            validated_data["published_at"] = timezone.now()

        # Upload image to S3 if provided
        if image_file:
            try:
                s3_url = instance.upload_image_to_s3(image_file)
                instance.image.name = s3_url  # Store S3 URL in ImageField
                instance.save(update_fields=["image"])
            except Exception as e:
                raise serializers.ValidationError({"image": str(e)})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


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
        if obj.image:
            # Return the raw S3 URL directly (stored in image.name)
            image_path = obj.image.name
            if image_path and image_path.startswith("http"):
                return image_path
            # Fallback for local files
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
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
        if obj.image:
            # If it's an S3 URL, return it directly
            if obj.image.name.startswith("http"):
                return obj.image.name
            # Otherwise, build absolute URI for local files
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_highlights(self, obj: News) -> Optional[Dict[str, Any]]:
        """Create an optional highlights summary. Keeps things lightweight for UI."""

        # Simple heuristic: first 200 chars as summary and first line as heading
        if not obj.content:
            return None
        summary = obj.content.strip()[:200]
        first_line = obj.content.strip().split("\n", 1)[0]
        return {"heading": first_line[:120], "summary": summary}
