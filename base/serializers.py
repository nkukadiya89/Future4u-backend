from rest_framework import serializers

from utils.datetime_formatter import format_datetime


class AuditFieldsMixin(serializers.Serializer):
    """
    Shared audit-readonly declaration + datetime formatter helper.
    """

    audit_read_only_fields = ("created_at", "created_by", "updated_at", "updated_by")

    @staticmethod
    def format_audit_datetime(value):
        return format_datetime(value)


class SoftDeleteMixin:
    """
    Serializer helper for common non-archived filtering.
    """

    archive_field = "deleted"

    @classmethod
    def non_archived_queryset(cls, queryset):
        return queryset.filter(**{cls.archive_field: False})
