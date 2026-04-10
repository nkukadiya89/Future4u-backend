from rest_framework import serializers

from base.serializers import AuditFieldsMixin
from language_master.models import Language, LanguageImportBatch
from language_master.services import language_service


class LanguageSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    is_archived = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Language
        fields = (
            "id", "name", "code", "description",
            "is_active", "is_archived",
            "created_at", "updated_at",
        )
        read_only_fields = ("is_archived",)

    def get_created_at(self, obj):
        return self.format_audit_datetime(obj.created_at)

    def get_updated_at(self, obj):
        return self.format_audit_datetime(obj.updated_at)

    def get_is_archived(self, obj):
        return bool(getattr(obj, "deleted", False))

    def validate_code(self, value):
        value = (value or "").strip().upper()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        exclude = self.instance.pk if getattr(self.instance, "pk", None) else None
        if language_service.case_insensitive_code_exists(code=value, exclude_pk=exclude):
            raise serializers.ValidationError("Language code must be unique (case-insensitive).")
        return value

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        return language_service.create_language(user=user, validated_data=validated_data)

    def update(self, instance, validated_data):
        user = self.context["request"].user
        return language_service.update_language(language=instance, user=user, validated_data=validated_data)


class LanguageDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ("id", "code", "name")


class LanguageChangeStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class LanguageBulkIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class LanguageImportBatchSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField(read_only=True)
    completed_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LanguageImportBatch
        fields = ("id", "created_at", "total_rows", "imported_count", "failed_count", "completed_at")

    def get_created_at(self, obj):
        return self.format_audit_datetime(obj.created_at)

    def get_completed_at(self, obj):
        return self.format_audit_datetime(obj.completed_at)
