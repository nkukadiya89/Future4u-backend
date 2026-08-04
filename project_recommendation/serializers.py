from rest_framework import serializers

from project_recommendation.models import ProjectRecommendation


class ProjectRecommendationSerializer(serializers.ModelSerializer):
    """Read serializer for saved project recommendations.

    Mirrors the POST generate response shape (domain, domain_category,
    assessment_id, education_level, projects) so the frontend renders
    saved data the same way as freshly generated data.
    """

    assessment_id = serializers.SerializerMethodField()
    projects = serializers.SerializerMethodField()

    class Meta:
        model = ProjectRecommendation
        fields = (
            "id",
            "profile_type",
            "assessment_id",
            "domain",
            "domain_category",
            "education_level",
            "token_usage",
            "last_recommended_at",
            "projects",
        )

    def get_assessment_id(self, obj):
        return (
            obj.student_assessment_id
            or obj.parent_assessment_id
            or obj.professional_assessment_id
        )

    def get_projects(self, obj):
        raw = obj.raw_ai_response
        if isinstance(raw, dict):
            return raw.get("projects", [])
        return []
