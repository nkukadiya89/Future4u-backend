from rest_framework import serializers
from business_category.models import BusinessCategory


class BusinessCategorySerializers(serializers.ModelSerializer):
    class Meta:
        model = BusinessCategory
        fields = ["id", "business_category"]

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
        instance.business_category = validated_data.get(
            "business_category", instance.business_category
        )
        instance.updated_by = user
        instance.save()
        return instance


class BusinessCategoryDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Temper dropdown API - active and non-archived only"""

    class Meta:
        model = BusinessCategory
        fields = ["id", "business_category"]
