from rest_framework import serializers

from common.serializers import BaseModelSerializer
from assessment.models import Option, Question, StudentAssessment, UserResponse
from domain.models import Domain
from user.serializers import UserQuickSerializer

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


class UserResponseSerializer(serializers.ModelSerializer):
    assessment = serializers.PrimaryKeyRelatedField(queryset=StudentAssessment.objects.all(), required=False)
    user = UserQuickSerializer(read_only=True)

    class Meta:
        model = UserResponse
        fields = ["id","assessment" ,"user", "question", "selected_option", "score_value"]
        read_only_fields = ["id", "user", "score_value"]

    def validate(self, attrs):
        question = attrs.get("question")
        selected_option = attrs.get("selected_option")
        score_value = attrs.get("score_value")

        if selected_option and question and selected_option.question_id != question.id:
            raise serializers.ValidationError(
                {"selected_option": "Selected option does not belong to this question."}
            )

        if (
            selected_option
            and score_value is not None
            and score_value != selected_option.score_value
        ):
            raise serializers.ValidationError(
                {"score_value": "score_value must match selected_option score."}
            )

        request = self.context.get("request") if hasattr(self, "context") else None
        req_user = getattr(request, "user", None) if request else None
        assessment = attrs.get("assessment")
        if assessment and question:
            exists = UserResponse.objects.filter(assessment=assessment, question=question)
            if self.instance:
                exists = exists.exclude(pk=self.instance.pk)
            if exists.exists():
                raise serializers.ValidationError(
                    {"question": "Response already exists for this assessment and question."}
                )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        return UserResponse.objects.create(user=user, **validated_data)


class StudentAssessmentSerializer(BaseModelSerializer):
    domain_category = serializers.PrimaryKeyRelatedField(
        queryset=Domain.objects.filter(is_active=True, deleted=False),
        required=False,
        allow_null=True,
    )
    domain = serializers.PrimaryKeyRelatedField(
        queryset=Domain.objects.filter(is_active=True, deleted=False),
        required=False,
        allow_null=True,
    )
    user = UserQuickSerializer(read_only=True)
    
    class Meta:
        model = StudentAssessment
        fields = BaseModelSerializer.Meta.fields + [
            "domain_category",
            "domain",
            "career_direction",
            "parent_support",
            "concerns",
            "career_values",
            "user_goals",
            "current_screen",
            "user",
            "is_completed",
        ]
        read_only_fields = ("id", "user", "current_screen", "created_at", "updated_at")

    def validate(self, attrs):
        category = attrs.get("domain_category")
        domain = attrs.get("domain")
        if self.instance:
            if category is None and self.instance.domain_category_id:
                category = self.instance.domain_category
            if domain is None and self.instance.domain_id:
                domain = self.instance.domain

        if category and category.parent_id is not None:
            raise serializers.ValidationError(
                {"domain_category": "Selected category must be a parent domain."}
            )

        if domain and domain.parent_id is None:
            raise serializers.ValidationError(
                {"domain": "Selected domain must be a child domain."}
            )

        if category and domain and domain.parent_id != category.id:
            raise serializers.ValidationError(
                {"domain": "Selected domain must belong to selected category."}
            )

        return attrs

class StudentAssessmentCreateSerializer(BaseModelSerializer):
    class Meta:
        model = StudentAssessment
        fields = [
            "id",
            "current_screen",
            "is_completed",
        ]


class NextQuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "question_text",
            "dimension",
            "options",
        ]

class AssessmentResponseSerializer(serializers.Serializer):
    assessment = serializers.IntegerField()
    question = serializers.IntegerField()
    selected_option = serializers.IntegerField()
