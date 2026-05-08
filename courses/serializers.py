from rest_framework import serializers

from .models import (
    Course,
    CourseEnrollment,
    CourseOutcome,
    CourseReview,
    ProfileCoursePreference,
)


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "updated_by",
            "deleted",
            "deleted_by",
            "deleted_at",
        ]


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseEnrollment
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "updated_by",
            "deleted",
            "deleted_by",
            "deleted_at",
            "enrolled_at",
        ]


class CourseOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseOutcome
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "updated_by",
            "deleted",
            "deleted_by",
            "deleted_at",
        ]


class CourseReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseReview
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "updated_by",
            "deleted",
            "deleted_by",
            "deleted_at",
        ]


class ProfileCoursePreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileCoursePreference
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "updated_by",
            "deleted",
            "deleted_by",
            "deleted_at",
        ]
