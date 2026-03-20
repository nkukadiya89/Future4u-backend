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



class BusinessCategoryDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Temper dropdown API - active and non-archived only"""

    class Meta:
        model = BusinessCategory
        fields = ["id", "business_category"]
