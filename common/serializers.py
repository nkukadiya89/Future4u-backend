from rest_framework import serializers

from base.serializers import AuditFieldsMixin
from common.mixins.serializer_mixins import TrackDateMixin, DeletedAtMixin
from user.serializers import UserQuickSerializer


class BaseModelSerializer(
    AuditFieldsMixin,
    TrackDateMixin,
    DeletedAtMixin,
    serializers.ModelSerializer,
):
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
