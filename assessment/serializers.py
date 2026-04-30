from rest_framework import serializers
from django.db import transaction

from common.serializers import BaseModelSerializer
from assessment.models import AssessmentInterestCategory, Option, Question


class AssessmentInterestCategorySerializer(BaseModelSerializer):
    category_image = serializers.ImageField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta(BaseModelSerializer.Meta):
        model = AssessmentInterestCategory
        fields = BaseModelSerializer.Meta.fields + [
            "category_code",
            "category_name",
            "category_image_url",
            "category_image",
            "sequence_order",
            "is_active",
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


class StudentInterestCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentInterestCategory
        fields = [
            "id",
            "category_code",
            "category_name",
            "category_image_url",
            "sequence_order",
        ]


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "option_text", "score_value", "sequence_order"]


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)
    mapped_domains = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    mapped_streams = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    education_level_code = serializers.CharField(
        source="education_level.level_code", read_only=True, default=None
    )

    class Meta:
        model = Question
        fields = [
            "id",
            "question_text",
            "dimension",
            "question_type",
            "sequence_order",
            "signal_strength",
            "mapped_domains",
            "mapped_streams",
            "education_level",
            "education_level_code",
            "target_stream",
            "is_active",
            "options",
        ]


class AssessmentSubmitItemSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    option_id = serializers.IntegerField()


class AssessmentSubmitSerializer(serializers.Serializer):
    responses = AssessmentSubmitItemSerializer(many=True)


class StudentInterestSaveSerializer(serializers.Serializer):
    domain_interests = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=AssessmentInterestCategory.objects.filter(
            is_active=True,
            deleted=False,
        ),
        allow_empty=False,
    )

    def validate_domain_interests(self, value):
        if len(value) > 2:
            raise serializers.ValidationError("Select up to 2 interest areas.")
        if len({item.id for item in value}) != len(value):
            raise serializers.ValidationError("Duplicate interest areas are not allowed.")
        return value
