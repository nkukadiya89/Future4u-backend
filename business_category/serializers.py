from django.utils.timezone import now
from rest_framework import serializers
from business_category.models import BusinessCategory
from common.serializers import BaseModelSerializer
from utils.datetime_formatter import format_datetime


class BusinessCategorySerializers(BaseModelSerializer):
    class Meta:
        model = BusinessCategory
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "business_category",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def create(self, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance = BusinessCategory.objects.create(
            business_category=validated_data.get("business_category"),
            created_by=user,
        )
        return instance

    def update(self, instance, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance.business_category = validated_data.get("business_category", instance.business_category)
        instance.updated_by = user
        instance.updated_at = now()
        instance.save()
        return instance


class BusinessCategoryArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = BusinessCategory
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        for deleted_id in deleted_ids:
            try:
                business_category = BusinessCategory.objects.get(id=deleted_id)
                business_category.deleted = True
                if hasattr(business_category, "deleted_by"):
                    business_category.deleted_by = user
                if hasattr(business_category, "deleted_at"):
                    business_category.deleted_at = now()
                business_category.save()
            except BusinessCategory.DoesNotExist:
                raise serializers.ValidationError("Business category does not exist")

        return business_category


class BusinessCategoryRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = BusinessCategory
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                business_category = BusinessCategory.objects.get(id=deleted_id)
                business_category.deleted = False
                business_category.deleted_by = None
                business_category.deleted_at = None
                business_category.updated_at = now()
                business_category.save()
            except BusinessCategory.DoesNotExist:
                raise serializers.ValidationError("Business Category does not exist")

        return business_category


class BusinessCategoryArchiveListSerializer(BaseModelSerializer):
    # created_at = serializers.SerializerMethodField(read_only=True)
    # updated_at = serializers.SerializerMethodField(read_only=True)
    # deleted_at = serializers.SerializerMethodField(read_only=True)
    # created_by_name = serializers.SerializerMethodField()
    # updated_by_name = serializers.SerializerMethodField()
    # deleted_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BusinessCategory
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "business_category",
            # "deleted_by_name",
            # "deleted_at",
            # "deleted",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
            "deleted_by": {"write_only": True},
        }

    # def get_created_at(self, obj):
    #     return format_datetime(getattr(obj, "created_at", None))

    # def get_created_by_name(self, obj):
    #     return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else None

    # def get_updated_at(self, obj):
    #     return format_datetime(getattr(obj, "updated_at", None))

    # def get_updated_by_name(self, obj):
    #     return f"{obj.updated_by.first_name} {obj.updated_by.last_name}" if obj.updated_by else None

    # def get_deleted_at(self, obj):
    #     return format_datetime(getattr(obj, "deleted_at", None))

    # def get_deleted_by_name(self, obj):
    #     return f"{obj.deleted_by.first_name} {obj.deleted_by.last_name}" if obj.deleted_by else None
