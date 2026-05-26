from rest_framework import serializers

from common.serializers import BaseModelSerializer

from .models import CareerRecommendation, CareerRecommendationSuggestion


class CareerRecommendationSuggestionSerializer(BaseModelSerializer):
    """Used by compare API (needs suggestion row ids)."""

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


class CareerRecommendationSerializer(BaseModelSerializer):
    """
    Career payload lives in raw_ai_response (top_suggestions, easy_decision_making).
    DB suggestion rows exist for compare/?suggestion_ids= only.
    """

    suggestions = serializers.SerializerMethodField()

    class Meta:
        model = CareerRecommendation
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "user",
            "assessment",
            "raw_ai_response",
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
