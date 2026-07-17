from rest_framework import serializers

from activity_log.models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", default=None)
    user_name = serializers.CharField(source="user.full_name", default=None)
    user_type = serializers.CharField(source="user.user_type", default=None)

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "user_type",
            "event",
            "description",
            "entity_type",
            "entity_id",
            "metadata",
            "created_at",
        ]
