from rest_framework import serializers

from common.mixins.serializer_mixins import DateFieldsMixin, UserNameMixin
from token_override.models import TokenOverride
from utils.datetime_formatter import format_datetime


class TokenOverrideSerializer(
    DateFieldsMixin, UserNameMixin, serializers.ModelSerializer
):
    user_name = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TokenOverride
        fields = [
            "id",
            "user",
            "user_name",
            "entity_type",
            "entity_user_id",
            "extra_monthly_tokens",
            "valid_until",
            "is_active",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
            "created_at",
            "updated_at",
            "deleted",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.full_name or obj.user.email
        if obj.entity_type:
            return f"{dict(TokenOverride.ENTITY_TYPES).get(obj.entity_type, obj.entity_type)}"
        return None

    def get_created_at(self, obj):
        return format_datetime(getattr(obj, "created_at", None))

    def get_updated_at(self, obj):
        return format_datetime(getattr(obj, "updated_at", None))

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None

    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return f"{obj.updated_by.first_name} {obj.updated_by.last_name}".strip()
        return None
