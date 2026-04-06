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
            "interest_weight",
            "aptitude_weight",
            "personality_weight",
            "work_style_weight",
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
            raise serializers.ValidationError(
                "Domain code must be unique (case-insensitive)."
            )
        return value

    def validate(self, attrs):
        """
        Affinity weights validation:
        - allow all null/omitted (meaning: fallback weights will be used)
        - if any weight provided, require all 4 and ensure they sum to 1.0
        """
        attrs = super().validate(attrs)
        keys = ("interest_weight", "aptitude_weight", "personality_weight", "work_style_weight")

        # Determine the final values (include instance values on partial update)
        values = []
        provided_count = 0
        for k in keys:
            if k in attrs:
                v = attrs.get(k)
                provided_count += 1 if v is not None else 0
                values.append(v)
            else:
                v = getattr(self.instance, k, None) if self.instance is not None else None
                values.append(v)

        any_set = any(v is not None for v in values)
        if not any_set:
            return attrs
        if any(v is None for v in values):
            raise serializers.ValidationError({k: "Provide all 4 weights, or leave all blank." for k in keys})
        total = float(sum(float(v) for v in values))
        if abs(total - 1.0) > 0.001:
            raise serializers.ValidationError({k: "Weights must sum to 1.0." for k in keys})
        return attrs

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
