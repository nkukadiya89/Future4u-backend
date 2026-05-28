from rest_framework import serializers

from common.serializers import BaseModelSerializer

from .models import CareerRecommendation, CareerRecommendationSuggestion


class CareerRecommendationSuggestionSortSerializer(BaseModelSerializer):
    class Meta:
        model = CareerRecommendationSuggestion
        fields = [
            "id",
            "career_name",
            "match_percentage",
         ]

class CareerRecommendationSerializer(BaseModelSerializer):
    suggestions = CareerRecommendationSuggestionSortSerializer(many=True, read_only=True)

    class Meta:
        model = CareerRecommendation
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "user",
            "assessment",
            "suggestions",
            "easy_decision_making",
            "last_recommended_at",

        ]

class CareerRecommendationSuggestionSerializer(BaseModelSerializer):
    class Meta:
        model = CareerRecommendationSuggestion
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "recommendation",
            "career_name",
            "match_percentage",
            "ai_insight",
            "why_this_career",
            "required_skills",
            "required_education",
            "career_factors",
            "career_roadmap",
            "display_order",
        ]

class CareerRecommendationDetailSerializer(BaseModelSerializer):
    suggestions = CareerRecommendationSuggestionSerializer(many=True, read_only=True)

    suggestions = serializers.SerializerMethodField()

    class Meta:
        model = CareerRecommendation
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "assessment",
            "suggestions",
            "easy_decision_making",
            "suggestions",
            "last_recommended_at",
        ]

    def get_suggestions(self, obj):
        suggestions = getattr(obj, "active_suggestions", None)
        if suggestions is None:
            suggestions = obj.suggestions.filter(deleted=False).order_by(
                "display_order"
            )
        return CareerRecommendationSuggestionSerializer(suggestions, many=True).data
