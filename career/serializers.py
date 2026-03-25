from rest_framework import serializers

from base.serializers import AuditFieldsMixin
from career.models import Career, CareerImportBatch, CareerImportError
from career.services import career_service
from user.serializers import UserQuickSerializer


class CareerSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    min_education_level_id = serializers.UUIDField(source="min_education_level.id", read_only=True)
    min_education_level_code = serializers.CharField(source="min_education_level.level_code", read_only=True)
    min_education_level_name = serializers.CharField(source="min_education_level.display_name", read_only=True)
    max_education_level_id = serializers.UUIDField(source="max_education_level.id", read_only=True)
    max_education_level_code = serializers.CharField(source="max_education_level.level_code", read_only=True)
    max_education_level_name = serializers.CharField(source="max_education_level.display_name", read_only=True)

    class Meta:
        model = Career
        fields = (
            "id",
            "career_code",
            "career_name",
            "description",
            "min_education_level",
            "min_education_level_id",
            "min_education_level_code",
            "min_education_level_name",
            "max_education_level",
            "max_education_level_id",
            "max_education_level_code",
            "max_education_level_name",
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

    def validate_career_code(self, value):
        value = (value or "").strip().lower()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        exclude = self.instance.pk if getattr(self.instance, "pk", None) else None
        if career_service.case_insensitive_code_exists(code=value, exclude_pk=exclude):
            raise serializers.ValidationError("Career code must be unique (case-insensitive).")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        min_edu = attrs.get("min_education_level", getattr(self.instance, "min_education_level", None))
        max_edu = attrs.get("max_education_level", getattr(self.instance, "max_education_level", None))
        if min_edu is None:
            raise serializers.ValidationError({"min_education_level": "This field is required."})
        if max_edu and max_edu.sequence_order < min_edu.sequence_order:
            raise serializers.ValidationError({"max_education_level": "Max education level cannot be below min education level."})
        return attrs

    def validate_min_education_level(self, value):
        if value is None:
            raise serializers.ValidationError("This field is required.")
        if getattr(value, "deleted", False):
            raise serializers.ValidationError("Invalid education level.")
        return value

    def validate_max_education_level(self, value):
        if value and getattr(value, "deleted", False):
            raise serializers.ValidationError("Invalid education level.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        return career_service.create_career(
            user=user,
            validated_data=validated_data,
        )

    def update(self, instance, validated_data):
        user = self.context["request"].user
        return career_service.update_career(
            career=instance,
            user=user,
            validated_data=validated_data,
        )


class CareerDropdownSerializer(serializers.ModelSerializer):
    min_education_level_id = serializers.UUIDField(source="min_education_level.id", read_only=True)
    min_education_level_code = serializers.CharField(source="min_education_level.level_code", read_only=True)
    min_education_level_name = serializers.CharField(source="min_education_level.display_name", read_only=True)
    max_education_level_id = serializers.UUIDField(source="max_education_level.id", read_only=True)
    max_education_level_code = serializers.CharField(source="max_education_level.level_code", read_only=True)
    max_education_level_name = serializers.CharField(source="max_education_level.display_name", read_only=True)

    class Meta:
        model = Career
        fields = (
            "id",
            "career_code",
            "career_name",
            "min_education_level_id",
            "min_education_level_code",
            "min_education_level_name",
            "max_education_level_id",
            "max_education_level_code",
            "max_education_level_name",
        )


class CareerChangeStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class CareerBulkIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class CareerImportBatchSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    completed_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CareerImportBatch
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


class CareerImportErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerImportError
        fields = ("id", "batch_id", "row_number", "message", "row_data")


class CareerBulkImportSerializer(serializers.Serializer):
    rows = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )

