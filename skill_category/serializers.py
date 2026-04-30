from rest_framework import serializers
from common.serializers import BaseModelSerializer
from skill_category.models import SkillCategory, AssessmentInterestValue, AssessmentGoal
from django.db import transaction


class SkillCategorySerializer(BaseModelSerializer):
    category_image = serializers.ImageField(write_only=True, required=False, allow_null=True)

    class Meta(BaseModelSerializer.Meta):
        model = SkillCategory
        fields = BaseModelSerializer.Meta.fields + [
            "category_name",
            "category_image_url",
            "category_image",
        ]
        extra_kwargs = {
            "category_image_url": {
                "required": False,
                "allow_null": True,
                "allow_blank": True,
                "read_only": True,
            },
        }
    @transaction.atomic
    def create(self, validated_data):
        category_image = validated_data.pop("category_image", None)
        instance = super().create(validated_data)
        if category_image:
            instance.upload_category_image(category_image)
        return instance
    @transaction.atomic
    def update(self, instance, validated_data):
        category_image = validated_data.pop("category_image", None)
        instance = super().update(instance, validated_data)
        if category_image:
            instance.upload_category_image(category_image)
        return instance


class SkillCategoryDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillCategory
        fields = ["id", "category_name", "category_image_url"]


class AssessmentInterestValueSerializer(BaseModelSerializer):
    category_image = serializers.ImageField(write_only=True, required=False, allow_null=True)

    class Meta(BaseModelSerializer.Meta):
        model = AssessmentInterestValue
        fields = BaseModelSerializer.Meta.fields + [
            "category_name",
            "category_image_url",
            "category_image",
        ]
        extra_kwargs = {
            "category_image_url": {
                "required": False,
                "allow_null": True,
                "allow_blank": True,
                "read_only": True,
            },
        }

    @transaction.atomic
    def create(self, validated_data):
        category_image = validated_data.pop("category_image", None)
        instance = super().create(validated_data)
        if category_image:
            instance.upload_category_image(category_image)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        category_image = validated_data.pop("category_image", None)
        instance = super().update(instance, validated_data)
        if category_image:
            instance.upload_category_image(category_image)
        return instance


class AssessmentInterestValueDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentInterestValue
        fields = ["id", "category_name", "category_image_url"]


class AssessmentGoalSerializer(BaseModelSerializer):
    image = serializers.ImageField(write_only=True, required=False, allow_null=True)

    class Meta(BaseModelSerializer.Meta):
        model = AssessmentGoal
        fields = BaseModelSerializer.Meta.fields + [
            "name",
            "image_url",
            "image",
        ]
        extra_kwargs = {
            "image_url": {
                "required": False,
                "allow_null": True,
                "allow_blank": True,
                "read_only": True,
            },
        }

    @transaction.atomic
    def create(self, validated_data):
        image = validated_data.pop("image", None)
        instance = super().create(validated_data)
        if image:
            instance.upload_image(image)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        image = validated_data.pop("image", None)
        instance = super().update(instance, validated_data)
        if image:
            instance.upload_image(image)
        return instance


class AssessmentGoalDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentGoal
        fields = ["id", "name", "image_url"]
