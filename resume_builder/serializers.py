"""DRF serializers for the Resume Builder Path B API."""

from rest_framework import serializers

from resume_builder.models import GeneratedResume, ResumeTemplate


class ResumeTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeTemplate
        fields = [
            "code",
            "name",
            "description",
            "preview_image",
            "category",
            "is_active",
            "sort_order",
        ]


class GeneratedResumeListSerializer(serializers.ModelSerializer):
    """History items - deliberately excludes the full resume_json."""

    class Meta:
        model = GeneratedResume
        fields = ["id", "template", "resume_type", "tokens_used", "created_at"]


class GeneratedResumeDetailSerializer(serializers.ModelSerializer):
    resume_id = serializers.IntegerField(source="id", read_only=True)
    resume = serializers.JSONField(source="resume_json")

    class Meta:
        model = GeneratedResume
        fields = [
            "resume_id",
            "id",
            "template",
            "resume_type",
            "resume",
            "tokens_used",
            "created_at",
        ]
