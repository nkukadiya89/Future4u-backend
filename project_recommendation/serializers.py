from rest_framework import serializers

from project_recommendation.models import ProjectRecommendation


class ProjectRecommendationSerializer(serializers.ModelSerializer):
    """Read serializer for saved project recommendations.

    Mirrors the POST generate response shape (domain, domain_category,
    education_level, overview, projects) so the frontend renders saved
    data the same way as freshly generated data.
    """

    projects = serializers.SerializerMethodField()

    class Meta:
        model = ProjectRecommendation
        fields = (
            "id",
            "profile_type",
            "domain",
            "domain_category",
            "overview",
            "token_usage",
            "last_recommended_at",
            "projects",
        )

    def get_projects(self, obj):
        raw = obj.raw_ai_response
        if isinstance(raw, dict):
            return raw.get("projects", [])
        return []

