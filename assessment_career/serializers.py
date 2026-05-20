from rest_framework import serializers
from .models import CareerRecommendation, CareerRecommendationSuggestion
from common.serializers import BaseModelSerializer

class CareerRecommendationSuggestionSerializer(BaseModelSerializer):
    class Meta:
        model = CareerRecommendationSuggestion
        fields = BaseModelSerializer.Meta.fields+[
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

    class Meta:
        model = CareerRecommendation
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "user",
            "assessment",
            "raw_ai_response",
            "easy_decision_making",
            "last_recommended_at",
        ]
