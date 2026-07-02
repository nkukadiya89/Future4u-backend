from common.serializers import BaseModelSerializer

from .models import (
    CareerRecommendation,
    CareerSuggestion,
)


class CareerSuggestionSortSerializer(BaseModelSerializer):
    class Meta:
        model = CareerSuggestion
        fields = [
            "id",
            "career_name",
            "match_percentage",
        ]


class CareerRecommendationSerializer(BaseModelSerializer):
    suggestions = CareerSuggestionSortSerializer(many=True, read_only=True)

    class Meta:
        model = CareerRecommendation
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "user",
            "profile_type",
            "student_assessment",
            "parent_assessment",
            "professional_assessment",
            "suggestions",
            "easy_decision_making",
            "last_recommended_at",
        ]


class CareerSuggestionSerializer(BaseModelSerializer):
    class Meta:
        model = CareerSuggestion
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


