from email.utils import format_datetime, localtime

from rest_framework import serializers
from user.serializers import UserQuickSerializer
class BaseModelSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)

    class Meta:
        model = None
        fields = [
            "id",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "deleted",  
        ]

        kwargs = {
            "created_by": {"read_only": True},
            "updated_by": {"read_only": True},
            "deleted_by": {"read_only": True},
        }
        

    def _format_dt(self, value):
        return localtime(value).strftime("%Y-%m-%d %H:%M:%S") if value else None

    def get_created_at(self, obj):
        return self._format_dt(obj.created_at)

    def get_updated_at(self, obj):
        return self._format_dt(obj.updated_at)
    
    def get_deleted_at(self, obj):
        return self._format_dt(obj.deleted_at)