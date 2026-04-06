from rest_framework import serializers

from education_level.models import (
    EducationLevel,
    EducationLevelImportBatch,
    EducationLevelImportError,
)
from education_level.services import education_level_service
from user.serializers import UserQuickSerializer
from utils.datetime_formatter import format_datetime


class AuditFieldsMixin:
    def format_audit_datetime(self, value):
        return format_datetime(value)


class EducationLevelSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)

    is_archived = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EducationLevel
        fields = (
            "id",
            "level_code",
            "display_name",
            "sequence_order",
            "min_age",
            "max_age",
            "is_active",
            "is_archived",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        )
        read_only_fields = ("is_archived",)

    def _format_dt(self, value):
        return self.format_audit_datetime(value)

    def get_created_at(self, obj):
        return self._format_dt(obj.created_at)

    def get_updated_at(self, obj):
        return self._format_dt(obj.updated_at)

    def get_is_archived(self, obj):
        return bool(obj.deleted)

    def validate_level_code(self, value):
        value = (value or "").strip().lower()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        exclude = self.instance.pk if getattr(self.instance, "pk", None) else None
        if education_level_service.case_insensitive_code_exists(
            code=value, exclude_pk=exclude
        ):
            raise serializers.ValidationError(
                "Level code must be unique (case-insensitive)."
            )
        return value

    def validate(self, attrs):
        min_age = attrs.get("min_age", getattr(self.instance, "min_age", None))
        max_age = attrs.get("max_age", getattr(self.instance, "max_age", None))
        if min_age is not None and max_age is not None and int(min_age) > int(max_age):
            raise serializers.ValidationError(
                {"max_age": "max_age must be greater than or equal to min_age."}
            )
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return education_level_service.create_level(
            user=user, validated_data=validated_data
        )

    def update(self, instance, validated_data):
        user = self.context["request"].user
        return education_level_service.update_level(
            level=instance,
            user=user,
            validated_data=validated_data,
        )


class EducationLevelDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationLevel
        fields = ("id", "level_code", "display_name", "sequence_order")


class EducationLevelChangeStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class EducationLevelBulkIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class EducationLevelReorderItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    sequence_order = serializers.IntegerField(min_value=1)


class EducationLevelReorderSerializer(serializers.Serializer):
    orders = EducationLevelReorderItemSerializer(many=True, allow_empty=False)


class EducationLevelImportBatchSerializer(
    AuditFieldsMixin, serializers.ModelSerializer
):
    created_by = UserQuickSerializer(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    completed_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EducationLevelImportBatch
        fields = (
            "id",
            "created_at",
            "created_by",
            "total_rows",
            "imported_count",
            "failed_count",
            "completed_at",
        )

    def _format_dt(self, value):
        return self.format_audit_datetime(value)

    def get_created_at(self, obj):
        return self._format_dt(obj.created_at)

    def get_completed_at(self, obj):
        return self._format_dt(obj.completed_at)


class EducationLevelImportErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationLevelImportError
        fields = ("id", "batch_id", "row_number", "message", "row_data")


class EducationLevelBulkImportSerializer(serializers.Serializer):
    rows = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )
