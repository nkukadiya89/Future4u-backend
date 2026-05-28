from rest_framework import serializers
from .models import Courses
from common.serializers import BaseModelSerializer

class CoursesSerializer(BaseModelSerializer):

    provider_name = serializers.SerializerMethodField()
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = Courses
        fields = [
            "id",
            "name",
            "course_type",
            "mode",
            "skills",
            "education_tags",
            "duration",
            "provider",
            "provider_name",
            "city",
            "city_name",
            "course_overview",
            "why_this_course",
            "certification_info",
            "course_content",
        ]
    def get_provider_name(self, obj):
        if obj.provider:
            return obj.provider.full_name
        return None