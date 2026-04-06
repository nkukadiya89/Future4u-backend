from rest_framework import serializers

from base.serializers import AuditFieldsMixin
from skill.models import Skill, SkillImportBatch, SkillImportError, SkillType
from skill.services import skill_service
from user.serializers import UserQuickSerializer


class SkillSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    is_archived = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Skill
        fields = (
            "id",
            "skill_code",
            "skill_name",
            "skill_type",
            "description",
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
        return bool(getattr(obj, "deleted", False))

    def validate_skill_code(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        exclude = self.instance.pk if getattr(self.instance, "pk", None) else None
        if skill_service.case_insensitive_code_exists(code=value, exclude_pk=exclude):
            raise serializers.ValidationError(
                "Skill code must be unique (case-insensitive)."
            )
        return value

    def validate_skill_type(self, value):
        value = (value or "").strip().lower()
        allowed = {c for c, _ in SkillType.choices}
        if value not in allowed:
            raise serializers.ValidationError(
                f"Invalid skill_type. Allowed: {', '.join(sorted(allowed))}."
            )
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        return skill_service.create_skill(
            user=user,
            validated_data=validated_data,
        )

    def update(self, instance, validated_data):
        user = self.context["request"].user
        return skill_service.update_skill(
            skill=instance,
            user=user,
            validated_data=validated_data,
        )


class SkillDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ("id", "skill_code", "skill_name", "skill_type")


class SkillChangeStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class SkillBulkIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class SkillImportBatchSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    completed_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SkillImportBatch
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


class SkillImportErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillImportError
        fields = ("id", "batch_id", "row_number", "message", "row_data")


class SkillBulkImportSerializer(serializers.Serializer):
    rows = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )
