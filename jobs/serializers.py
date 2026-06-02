from rest_framework import serializers

from jobs.models import Job, JobApplication, JobPreference, SavedJob


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "updated_by",
            "deleted",
            "deleted_by",
            "deleted_at",
        ]

class JobPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPreference
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "updated_by",
            "deleted",
            "deleted_by",
            "deleted_at",
        ]


class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "updated_by",
            "deleted",
            "deleted_by",
            "deleted_at",
            "applied_at",
        ]


class SavedJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedJob
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "updated_by",
            "deleted",
            "deleted_by",
            "deleted_at",
            "saved_at",
        ]
