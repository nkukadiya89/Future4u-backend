from rest_framework import serializers

from stream.models import Stream, StreamImportBatch, StreamImportError
from stream.services import stream_service
from user.serializers import UserQuickSerializer
from utils.datetime_formatter import format_datetime


class AuditFieldsMixin:
    def format_audit_datetime(self, value):
        return format_datetime(value)


class StreamSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    is_archived = serializers.SerializerMethodField(read_only=True)
    education_level_id = serializers.UUIDField(
        source="education_level.id", read_only=True
    )
    education_level_code = serializers.CharField(
        source="education_level.level_code", read_only=True
    )
    education_level_name = serializers.CharField(
        source="education_level.display_name", read_only=True
    )

    class Meta:
        model = Stream
        fields = (
            "id",
            "stream_code",
            "stream_name",
            "sequence_order",
            "parent_safe_label",
            "traditional_equivalent",
            "description",
            "education_level",
            "education_level_id",
            "education_level_code",
            "education_level_name",
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

    def validate_stream_code(self, value):
        value = (value or "").strip().lower()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        exclude = self.instance.pk if getattr(self.instance, "pk", None) else None
        if stream_service.case_insensitive_code_exists(code=value, exclude_pk=exclude):
            raise serializers.ValidationError(
                "Stream code must be unique (case-insensitive)."
            )
        return value

    def validate_sequence_order(self, value):
        exclude = self.instance.pk if getattr(self.instance, "pk", None) else None
        if stream_service.sequence_exists(
            sequence_order=int(value), exclude_pk=exclude
        ):
            raise serializers.ValidationError("Sequence order must be unique.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        return stream_service.create_stream(user=user, validated_data=validated_data)

    def update(self, instance, validated_data):
        user = self.context["request"].user
        return stream_service.update_stream(
            stream=instance,
            user=user,
            validated_data=validated_data,
        )


class StreamDropdownSerializer(serializers.ModelSerializer):
    education_level_id = serializers.UUIDField(
        source="education_level.id", read_only=True
    )
    education_level_code = serializers.CharField(
        source="education_level.level_code", read_only=True
    )
    education_level_name = serializers.CharField(
        source="education_level.display_name", read_only=True
    )

    class Meta:
        model = Stream
        fields = (
            "id",
            "stream_code",
            "stream_name",
            "sequence_order",
            "education_level_id",
            "education_level_code",
            "education_level_name",
        )


class StreamChangeStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class StreamBulkIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class StreamImportBatchSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    completed_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StreamImportBatch
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


class StreamImportErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreamImportError
        fields = ("id", "batch_id", "row_number", "message", "row_data")


class StreamBulkImportSerializer(serializers.Serializer):
    rows = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )
