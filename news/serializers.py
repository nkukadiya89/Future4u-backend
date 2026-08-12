from __future__ import annotations

from typing import Any, Dict, Optional

from rest_framework import serializers

from .models import News


class BaseNewsSerializer(serializers.ModelSerializer):
    """Base serializer that returns a unified, filtered representation.

    It exposes the superset of all fields used by the different News serializers
    and filters out keys with `None` values so responses remain compact while
    consistent across list/detail/create/update views.
    """

    image = serializers.ImageField(required=False, allow_null=True)
    highlights = serializers.SerializerMethodField()

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
            "highlights",
        ]
        read_only_fields = ["id"]

    def get_image(self, obj: News) -> Optional[str]:
        if obj.image:
            image_path = getattr(obj.image, "name", None)
            if image_path and image_path.startswith("http"):
                return image_path
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_highlights(self, obj: News) -> Optional[Dict[str, Any]]:
        if not getattr(obj, "content", None):
            return None
        summary = obj.content.strip()[:200]
        first_line = obj.content.strip().split("\n", 1)[0]
        return {"heading": first_line[:120], "summary": summary}

    def to_representation(self, instance):
        """Return only keys that have a non-None value.

        Note: boolean False and numeric 0 are considered valid values and will
        be included because they are not `None`.
        The `image` field is preserved even when it is null so responses remain
        consistent across list/detail endpoints.
        """
        data = super().to_representation(instance)
        return {k: v for k, v in data.items() if v is not None or k == "image"}


class NewsSerializer(BaseNewsSerializer):
    """Serializer used for create/update operations."""

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


class NewsListSerializer(BaseNewsSerializer):
    """Compact representation for lists (unified response)."""

    class Meta(BaseNewsSerializer.Meta):
        pass


class NewsDetailSerializer(BaseNewsSerializer):
    """Detailed representation for single object views (unified response)."""

    class Meta(BaseNewsSerializer.Meta):
        pass
