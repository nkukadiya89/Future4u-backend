from django.utils import timezone as dj_tz
from rest_framework import serializers


class AuditFieldsMixin(serializers.Serializer):
    """
    Shared audit-readonly declaration + datetime formatter helper.
    """

    audit_read_only_fields = ("created_at", "created_by", "updated_at", "updated_by")

    @staticmethod
    def format_audit_datetime(value):
        return dj_tz.localtime(value).strftime("%Y-%m-%d %H:%M:%S") if value else None


class SoftDeleteMixin:
    """
    Serializer helper for common non-archived filtering.
    """

    archive_field = "deleted"

    @classmethod
    def non_archived_queryset(cls, queryset):
        return queryset.filter(**{cls.archive_field: False})
