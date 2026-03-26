from rest_framework import serializers

from domain_skill_mapping.models import DomainSkillMapping
from domain_skill_mapping.services import domain_skill_mapping_service
from user.serializers import UserQuickSerializer
from utils.datetime_formatter import format_datetime


class AuditFieldsMixin:
    def format_audit_datetime(self, value):
        return format_datetime(value)


class DomainSkillMappingSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    is_archived = serializers.SerializerMethodField(read_only=True)
    domain_name = serializers.CharField(source="domain.domain_name", read_only=True)
    domain_code = serializers.CharField(source="domain.domain_code", read_only=True)
    skill_name = serializers.CharField(source="skill.skill_name", read_only=True)
    skill_code = serializers.CharField(source="skill.skill_code", read_only=True)

    class Meta:
        model = DomainSkillMapping
        fields = (
            "id",
            "domain",
            "domain_name",
            "domain_code",
            "skill",
            "skill_name",
            "skill_code",
            "weight_score",
            "is_core",
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

    def validate_weight_score(self, value):
        score = int(value)
        if score < 0 or score > 100:
            raise serializers.ValidationError("Weight score must be between 0 and 100.")
        return score

    def validate(self, attrs):
        domain = attrs.get("domain", getattr(self.instance, "domain", None))
        skill = attrs.get("skill", getattr(self.instance, "skill", None))
        if domain and skill:
            exclude = self.instance.pk if getattr(self.instance, "pk", None) else None
            if domain_skill_mapping_service.pair_exists(domain_id=domain.pk, skill_id=skill.pk, exclude_pk=exclude):
                raise serializers.ValidationError({"non_field_errors": ["Domain-skill mapping already exists."]})
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return domain_skill_mapping_service.create_mapping(user=user, validated_data=validated_data)

    def update(self, instance, validated_data):
        user = self.context["request"].user
        return domain_skill_mapping_service.update_mapping(mapping=instance, user=user, validated_data=validated_data)


class DomainSkillMappingBulkIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class DomainSkillMappingBulkImportSerializer(serializers.Serializer):
    rows = serializers.ListField(child=serializers.DictField(), allow_empty=False)

