from rest_framework import serializers

from user_profile.models import ParentProfile


class ParentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentProfile
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "updated_by",
            "deleted",
            "deleted_by",
            "deleted_at",
        ]
