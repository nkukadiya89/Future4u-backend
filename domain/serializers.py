from rest_framework import serializers

from base.serializers import AuditFieldsMixin
from domain.models import Domain, DomainImportBatch, DomainImportError
from domain.services import domain_service
from user.serializers import UserQuickSerializer


class ParentDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ("id", "domain_code", "domain_name")


class DomainSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    parent = ParentDomainSerializer(read_only=True)
    parent_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    is_archived = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Domain
        fields = (
            "id",
            "domain_code",
            "domain_name",
            "parent",
            "parent_id",
            "parent_acceptance_level",
            "future_relevance_score",
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

    def validate_parent_acceptance_level(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Must be between 1 and 5.")
        return value

    def validate_future_relevance_score(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("Must be between 1 and 100.")
        return value

    def validate_domain_code(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        exclude = self.instance.pk if getattr(self.instance, "pk", None) else None
        if domain_service.case_insensitive_code_exists(code=value, exclude_pk=exclude):
            raise serializers.ValidationError("Domain code must be unique (case-insensitive).")
        return value

    def create(self, validated_data):
        validated_data.pop("parent_id", None)
        parent = None
        if "parent_id" in self.initial_data:
            raw = self.initial_data.get("parent_id")
            if raw not in (None, ""):
                parent = Domain.objects.filter(pk=raw, deleted=False).first()
                if not parent:
                    raise serializers.ValidationError({"parent_id": "Invalid parent."})
        user = self.context["request"].user
        return domain_service.create_domain(
            user=user,
            validated_data=validated_data,
            parent=parent,
        )

    def update(self, instance, validated_data):
        validated_data.pop("parent_id", None)
        user = self.context["request"].user
        update_parent = "parent_id" in self.initial_data
        parent = None
        if update_parent:
            raw = self.initial_data.get("parent_id")
            if raw in (None, ""):
                parent = None
            else:
                parent = Domain.objects.filter(pk=raw, deleted=False).first()
                if not parent:
                    raise serializers.ValidationError({"parent_id": "Invalid parent."})
        return domain_service.update_domain(
            domain=instance,
            user=user,
            validated_data=validated_data,
            parent=parent,
            update_parent=update_parent,
        )


class DomainDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ("id", "domain_code", "domain_name", "parent_id")


class DomainChangeStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class DomainBulkIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class DomainImportBatchSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    completed_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DomainImportBatch
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


class DomainImportErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainImportError
        fields = ("id", "batch_id", "row_number", "message", "row_data")


class DomainBulkImportSerializer(serializers.Serializer):
    rows = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )
