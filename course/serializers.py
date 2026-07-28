from rest_framework import serializers

from common.serializers import BaseModelSerializer
from user.models import User

from .models import CourseInquiry, Courses


class CoursesSerializer(BaseModelSerializer):

    provider_name = serializers.SerializerMethodField()
    country_name = serializers.CharField(source="country.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    course_provider_name = serializers.SerializerMethodField()

    # Accept AI-generated course_title as the course name
    course_title = serializers.CharField(
        source="name",
        required=False,
        write_only=True,
        help_text="AI-generated course title. Maps to the 'name' field.",
    )

    # Dropdown 1 — type of organisation posting this course
    provider_type = serializers.ChoiceField(
        choices=Courses.PROVIDER_TYPE_CHOICES,
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    # Dropdown 2 — course provider (institute/school-college user)
    course_provider = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(
            user_type__in=["school_college", "institute"],
            deleted=False,
        ),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Courses
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "name",
            "course_title",
            "course_type",
            "mode",
            "skills",
            "education_tags",
            "duration",
            "provider",
            "provider_name",
            "provider_type",
            "course_provider",
            "course_provider_name",
            "country",
            "country_name",
            "state",
            "state_name",
            "city",
            "city_name",
            "course_overview",
            "course_description",
            "why_this_course",
            "certification_info",
            "course_content",
            "course_price",
            "status",
        ]
        extra_kwargs = {
            "name": {"required": False},
        }

    def get_provider_name(self, obj):
        if obj.provider:
            return obj.provider.full_name
        return None

    def get_course_provider_name(self, obj):
        if obj.course_provider:
            if hasattr(obj.course_provider, "institute_profile"):
                name = obj.course_provider.institute_profile.institute_name
                if name:
                    return name
            if hasattr(obj.course_provider, "school_college_profile"):
                name = obj.course_provider.school_college_profile.institute_name
                if name:
                    return name
            return obj.course_provider.full_name
        return None

    def validate(self, attrs):
        if self.instance:
            # PATCH request
            name = attrs.get("name", self.instance.name)
        else:
            # POST request
            name = attrs.get("name")

        if not name:
            raise serializers.ValidationError({"name": "Course name is required."})

        return attrs


class CourseInquirySerializer(BaseModelSerializer):
    course_name = serializers.CharField(source="course.name", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = CourseInquiry
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "course",
            "course_name",
            "user",
            "user_name",
            "name",
            "phone",
            "email",
            "message",
            "status",
        ]
