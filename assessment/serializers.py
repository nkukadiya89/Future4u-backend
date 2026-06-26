from rest_framework import serializers

from assessment.models import (
    CareerDirection,
    CareerValue,
    Concern,
    Option,
    ParentAssessment,
    ParentCareerExpectation,
    ParentConstraint,
    Question,
    StudentAssessment,
    UserGoal,
    UserResponse,
)
from common.serializers import BaseModelSerializer
from domain.models import Domain
from user.serializers import UserQuickSerializer


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "option_text", "sequence_order"]


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


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id",
            "question_text",
            "dimension",
            "question_type",
        ]


class AssessmentQuestionResponseSerializer(serializers.ModelSerializer):
    question = AssessmentQuestionSerializer(read_only=True)
    selected_option = OptionSerializer(read_only=True)

    class Meta:
        model = UserResponse
        fields = [
            "id",
            "question",
            "selected_option",
        ]


class UserResponseSerializer(serializers.ModelSerializer):
    assessment = serializers.PrimaryKeyRelatedField(
        queryset=StudentAssessment.objects.all(), required=False
    )
    user = UserQuickSerializer(read_only=True)

    class Meta:
        model = UserResponse
        fields = ["id", "assessment", "user", "question", "selected_option"]
        read_only_fields = ["id", "user"]

    def validate(self, attrs):
        question = attrs.get("question")
        selected_option = attrs.get("selected_option")

        if selected_option and question and selected_option.question_id != question.id:
            raise serializers.ValidationError(
                {"selected_option": "Selected option does not belong to this question."}
            )

        if not selected_option:
            raise serializers.ValidationError(
                {"selected_option": "This field is required."}
            )

        assessment = attrs.get("assessment")
        if assessment and question:
            exists = UserResponse.objects.filter(
                assessment=assessment, question=question
            )
            if self.instance:
                exists = exists.exclude(pk=self.instance.pk)
            if exists.exists():
                raise serializers.ValidationError(
                    {
                        "question": "Response already exists for this assessment and question."
                    }
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
    domain_category_name = serializers.CharField(source="domain_category.domain_name", read_only=True, default=None)
    domain_name = serializers.CharField(source="domain.domain_name", read_only=True, default=None)
    career_direction_name = serializers.SerializerMethodField()
    concerns_name = serializers.SerializerMethodField()
    career_values_name = serializers.SerializerMethodField()
    user_goals_name = serializers.SerializerMethodField()
    user = UserQuickSerializer(read_only=True)
    responses = AssessmentQuestionResponseSerializer(many=True, read_only=True)

    class Meta:
        model = StudentAssessment
        fields = BaseModelSerializer.Meta.fields + [
            "domain_category",
            "domain_category_name",
            "domain",
            "domain_name",
            "career_direction",
            "career_direction_name",
            "parent_support",
            "concerns",
            "concerns_name",
            "career_values",
            "career_values_name",
            "user_goals",
            "user_goals_name",
            "current_screen",
            "user",
            "is_completed",
            "responses",
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
    def get_career_direction_name(self, obj):
        return list(obj.career_direction.values_list('name', flat=True))
    
    def get_concerns_name(self, obj):
        return list(obj.concerns.values_list("name", flat=True))

    def get_career_values_name(self, obj):
        return list(obj.career_values.values_list("name", flat=True))

    def get_user_goals_name(self, obj):
        return list(obj.user_goals.values_list("name", flat=True))

class StudentAssessmentCreateSerializer(BaseModelSerializer):
    class Meta:
        model = StudentAssessment
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "current_screen",
            "is_completed",
        ]


class ParentCareerExpectationSerializer(BaseModelSerializer):
    class Meta:
        model = ParentCareerExpectation
        fields = BaseModelSerializer.Meta.fields + ["name"]


class ParentConstraintSerializer(BaseModelSerializer):
    class Meta:
        model = ParentConstraint
        fields = BaseModelSerializer.Meta.fields + ["name"]


class ParentAssessmentSerializer(BaseModelSerializer):
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
    domain_category_name = serializers.CharField(
        source="domain_category.domain_name", read_only=True, default=None
    )
    domain_name = serializers.CharField(
        source="domain.domain_name", read_only=True, default=None
    )
    career_direction_name = serializers.SerializerMethodField()
    concerns_name = serializers.SerializerMethodField()
    parent_career_expectations_name = serializers.SerializerMethodField()
    limitations_name = serializers.SerializerMethodField()
    career_values_name = serializers.SerializerMethodField()
    user_goals_name = serializers.SerializerMethodField()
    child_name = serializers.SerializerMethodField()
    user = UserQuickSerializer(read_only=True)

    class Meta:
        model = ParentAssessment
        fields = BaseModelSerializer.Meta.fields + [
            "child",
            "child_name",
            "domain_category",
            "domain_category_name",
            "domain",
            "domain_name",
            "career_direction",
            "career_direction_name",
            "parent_support",
            "concerns",
            "concerns_name",
            "parent_career_expectations",
            "parent_career_expectations_name",
            "limitations",
            "limitations_name",
            "career_familiarity",
            "decision_style",
            "career_values",
            "career_values_name",
            "user_goals",
            "user_goals_name",
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

    def get_career_direction_name(self, obj):
        return list(obj.career_direction.values_list("name", flat=True))

    def get_concerns_name(self, obj):
        return list(obj.concerns.values_list("name", flat=True))

    def get_parent_career_expectations_name(self, obj):
        return list(obj.parent_career_expectations.values_list("name", flat=True))

    def get_limitations_name(self, obj):
        return list(obj.limitations.values_list("name", flat=True))

    def get_career_values_name(self, obj):
        return list(obj.career_values.values_list("name", flat=True))

    def get_user_goals_name(self, obj):
        return list(obj.user_goals.values_list("name", flat=True))

    def get_child_name(self, obj):
        if obj.child_id:
            return str(obj.child) if obj.child else None
        return None
    
class ParentAssessmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentAssessment
        fields = [
            "child",
            "domain_category",
            "domain",
            "career_direction",
            "parent_support",
            "concerns",
            "parent_career_expectations",
            "limitations",
            "career_familiarity",
            "decision_style",
            "career_values",
            "user_goals",
            "is_completed",
        ]

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
  

class NextQuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "question_text",
            "dimension",
            "question_type",
            "options",
        ]


class AssessmentResponseSerializer(serializers.Serializer):
    assessment = serializers.IntegerField()
    question = serializers.IntegerField()
    selected_option = serializers.IntegerField(required=False, allow_null=True)

    def to_internal_value(self, data):
        unknown_fields = set(data) - set(self.fields)
        if unknown_fields:
            raise serializers.ValidationError(
                {field: "Unknown field." for field in sorted(unknown_fields)}
            )
        return super().to_internal_value(data)



class ConcernSerializer(BaseModelSerializer):
    class Meta:
        model = Concern
        fields = BaseModelSerializer.Meta.fields + ["name"]

class CareerValueSerializer(BaseModelSerializer):
    class Meta:
        model = CareerValue
        fields = BaseModelSerializer.Meta.fields + ["name"]

class UserGoalSerializer(BaseModelSerializer):
    class Meta:
        model = UserGoal
        fields = BaseModelSerializer.Meta.fields + ["name"]

class CareerDirectionSerializer(BaseModelSerializer):
    class Meta:
        model = CareerDirection
        fields = BaseModelSerializer.Meta.fields + ["name"]
