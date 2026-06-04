from rest_framework import serializers
from .models import Courses, CourseInquiry
from common.serializers import BaseModelSerializer

class CoursesSerializer(BaseModelSerializer):

    provider_name = serializers.SerializerMethodField()
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = Courses
        fields = BaseModelSerializer.Meta.fields+[
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
    

class CourseInquirySerializer(BaseModelSerializer):
    course_name = serializers.CharField(source="course.name", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    class Meta:
        model = CourseInquiry
        fields = BaseModelSerializer.Meta.fields+[
            "id",
            "course",
            "course_name",
            "user",
            "user_name",
            "name",
            "phone",
            "email",
            "message",
        ]
