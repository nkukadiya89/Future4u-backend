from rest_framework import serializers

from assessment.models import Option, Question, UserResponse


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "option_text", "score_value", "sequence_order"]


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)
    mapped_domains = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    mapped_streams = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

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
            "target_stream",
            "is_active",
            "options",
        ]


class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserResponse
        fields = ["id", "user", "question", "selected_option", "score_value"]
        read_only_fields = ["id", "user"]

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
        if req_user and question:
            exists = UserResponse.objects.filter(user=req_user, question=question)
            if self.instance:
                exists = exists.exclude(pk=self.instance.pk)
            if exists.exists():
                raise serializers.ValidationError(
                    {"question": "Response already exists for this user and question."}
                )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        return UserResponse.objects.create(user=user, **validated_data)


class AssessmentSubmitItemSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    option_id = serializers.IntegerField()


class AssessmentSubmitSerializer(serializers.Serializer):
    responses = AssessmentSubmitItemSerializer(many=True)
