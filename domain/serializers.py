from rest_framework import serializers
import json
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
    data = serializers.CharField(write_only=True, required=False)
    domain_image_file = serializers.ImageField(
        write_only=True, required=False, allow_null=True
    )
    domain_code = serializers.CharField(required=False)
    domain_name = serializers.CharField(required=False)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    is_archived = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Domain
        fields = (
            "data",
            "domain_image_file",
            "domain_image",
            "id",
            "domain_code",
            "domain_name",
            "parent",
            "parent_id",
            "description",
            "is_active",
            "is_archived",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        )
        read_only_fields = ("is_archived", "domain_image")

    def validate(self, attrs):
        if "data" in attrs:
            data = attrs.get("data", "{}")
            try:
                parsed_data = json.loads(data) if isinstance(data, str) else data
            except json.JSONDecodeError:
                raise serializers.ValidationError({"data": "Invalid JSON format"})
            attrs.update(parsed_data)
            attrs["parsed_data"] = parsed_data
        else:
            attrs["parsed_data"] = attrs.copy()

        # Validate required fields after parsing (only for create)
        if not self.instance:
            errors = {}
            if not attrs.get("domain_code"):
                errors["domain_code"] = ["This field is required."]
            if not attrs.get("domain_name"):
                errors["domain_name"] = ["This field is required."]
            if errors:
                raise serializers.ValidationError(errors)

        attrs["domain_image_file"] = self.context["request"].FILES.get("domain_image")
        return attrs

    def _format_dt(self, value):
        return self.format_audit_datetime(value)

    def get_created_at(self, obj):
        return self._format_dt(obj.created_at)

    def get_updated_at(self, obj):
        return self._format_dt(obj.updated_at)

    def get_is_archived(self, obj):
        return bool(getattr(obj, "deleted", False))

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

    def create(self, validated_data):
        parsed_data = validated_data.pop("parsed_data", {})
        domain_image_file = validated_data.pop("domain_image_file", None)

        validated_data.pop("data", None)

        parent_id = parsed_data.get("parent_id")
        parent = None
        if parent_id and parent_id not in (None, ""):
            parent = Domain.objects.filter(pk=parent_id, deleted=False).first()
            if not parent:
                raise serializers.ValidationError({"parent_id": "Invalid parent."})

        user = self.context["request"].user
        domain = domain_service.create_domain(
            user=user,
            validated_data=parsed_data,
            parent=parent,
        )

        if domain_image_file:
            domain.upload_domain_image(domain_image_file)
            domain.refresh_from_db(fields=["domain_image"])

        return domain

    def update(self, instance, validated_data):
        parsed_data = validated_data.pop("parsed_data", {})
        domain_image_file = validated_data.pop("domain_image_file", None)

        # Remove non-model fields from validated_data
        validated_data.pop("data", None)

        user = self.context["request"].user
        update_parent = "parent_id" in parsed_data
        parent = None
        if update_parent:
            parent_id = parsed_data.get("parent_id")
            if parent_id in (None, ""):
                parent = None
            else:
                parent = Domain.objects.filter(pk=parent_id, deleted=False).first()
                if not parent:
                    raise serializers.ValidationError({"parent_id": "Invalid parent."})

        domain = domain_service.update_domain(
            domain=instance,
            user=user,
            validated_data=parsed_data,
            parent=parent,
            update_parent=update_parent,
        )

        if domain_image_file:
            domain.upload_domain_image(domain_image_file)
            domain.refresh_from_db(fields=["domain_image"])

        return domain


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
