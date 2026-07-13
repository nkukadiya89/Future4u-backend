from django.utils.timezone import now
from rest_framework import serializers

from common.mixins.serializer_mixins import (
    DateFieldsMixin,
    DeletedFieldsMixin,
    UserNameMixin,
)
from faq.models import FAQ


class FAQSerializers(DateFieldsMixin, UserNameMixin, serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = FAQ
        fields = [
            "id",
            "question",
            "answer",
            "created_by_name",
            "updated_by_name",
            "deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance = FAQ(**validated_data)
        instance.created_by = user
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for field in ["question", "answer", "deleted"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance.updated_by = user
        instance.updated_at = now()
        instance.save()
        return instance


class FAQArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = FAQ
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        for deleted_id in deleted_ids:
            try:
                faq = FAQ.objects.get(id=deleted_id)
                faq.deleted = True
                if hasattr(faq, "deleted_by"):
                    faq.deleted_by = user
                if hasattr(faq, "deleted_at"):
                    faq.deleted_at = now()
                faq.save()
            except FAQ.DoesNotExist:
                raise serializers.ValidationError("FAQ does not exist")

        return faq


# FAQ Archive Serializer
class FAQRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = FAQ
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                faq = FAQ.objects.get(id=deleted_id)
                faq.deleted = False
                faq.deleted_at = None
                faq.deleted_by = None
                faq.updated_at = now()
                faq.save()
            except FAQ.DoesNotExist:
                raise serializers.ValidationError("FAQ does not exist")

        return faq


class FAQArchiveListSerializer(
    DateFieldsMixin,
    UserNameMixin,
    DeletedFieldsMixin,
    serializers.ModelSerializer,
):
    created_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    deleted_by_name = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FAQ
        fields = [
            "id",
            "question",
            "answer",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
            "deleted_by",
            "deleted_by_name",
            "deleted_at",
            "deleted",
        ]
