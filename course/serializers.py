from rest_framework import serializers

from common.serializers import BaseModelSerializer
from education_level.serializers import EducationLevelDropdownSerializer
from user.models import User

from .models import CourseInquiry, CourseInquiryNote, Courses

class CoursesSerializer(BaseModelSerializer):

    created_by_name = serializers.SerializerMethodField()
    country_name = serializers.CharField(source="country.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    course_provider_name = serializers.SerializerMethodField()
    education_tags_name = EducationLevelDropdownSerializer(source="education_tags", many=True, read_only=True)
    course_title = serializers.CharField(
        source="name",
        required=False,
        write_only=True,
        help_text="AI-generated course title. Maps to the 'name' field.",
    )

    provider_type = serializers.ChoiceField(
        choices=Courses.PROVIDER_TYPE_CHOICES,
        required=False,
        allow_null=True,
        allow_blank=True,
    )

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
            "education_tags_name",
            "duration",
            "created_by",
            "created_by_name",
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

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.full_name
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
            name = attrs.get("name", self.instance.name)
        else:
            name = attrs.get("name")

        if not name:
            raise serializers.ValidationError({"name": "Course name is required."})

        return attrs


class CourseInquirySerializer(BaseModelSerializer):
    course_name = serializers.CharField(source="course.name", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    career_name = serializers.CharField(source="career_suggestion.career_name", read_only=True)
    assessment_score = serializers.CharField(source="career_suggestion.match_percentage", read_only=True)

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
            "career_suggestion",
            "career_name",
            "assessment_score",
        ]

class CourseInquiryNoteSerializer(BaseModelSerializer):

    class Meta:
        model = CourseInquiryNote
        fields = BaseModelSerializer.Meta.fields+[
            "id",
            "inquiry",
            "note",
        ]
        read_only_fields = ["inquiry"]

