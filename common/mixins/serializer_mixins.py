from django.utils.timezone import now
from rest_framework import serializers

from utils.datetime_formatter import format_datetime


class FormatDateMixin:
    """Wraps utils.datetime_formatter.format_datetime for master serializers."""

    def format_audit_datetime(self, value):
        return format_datetime(value)


class _DatetimeHelperMixin:
    def _format_dt(self, value):
        return self.format_audit_datetime(value)


class TrackDateMixin(_DatetimeHelperMixin):
    """created_at / updated_at via format_audit_datetime (base AuditFieldsMixin)."""

    def get_created_at(self, obj):
        return self._format_dt(obj.created_at)

    def get_updated_at(self, obj):
        return self._format_dt(obj.updated_at)


class DeletedAtMixin(_DatetimeHelperMixin):
    def get_deleted_at(self, obj):
        return self._format_dt(getattr(obj, "deleted_at", None))


class ImportDateMixin(_DatetimeHelperMixin):
    """Import batch serializers: created_at and completed_at."""

    def get_created_at(self, obj):
        return self._format_dt(obj.created_at)

    def get_completed_at(self, obj):
        return self._format_dt(obj.completed_at)


class ArchiveStatusMixin:
    def get_is_archived(self, obj):
        return bool(getattr(obj, "deleted", False))


class ArchiveStatusDeletedMixin:
    def get_is_archived(self, obj):
        return bool(obj.deleted)


class DateFieldsMixin:
    def get_created_at(self, obj):
        return format_datetime(getattr(obj, "created_at", None))

    def get_updated_at(self, obj):
        return format_datetime(getattr(obj, "updated_at", None))


class UserNameMixin:
    def get_created_by_name(self, obj):
        return (
            f"{obj.created_by.first_name} {obj.created_by.last_name}"
            if obj.created_by
            else None
        )

    def get_updated_by_name(self, obj):
        return (
            f"{obj.updated_by.first_name} {obj.updated_by.last_name}"
            if obj.updated_by
            else None
        )


class DeletedFieldsMixin:
    def get_deleted_at(self, obj):
        return format_datetime(getattr(obj, "deleted_at", None))

    def get_deleted_by_name(self, obj):
        return (
            f"{obj.deleted_by.first_name} {obj.deleted_by.last_name}"
            if obj.deleted_by
            else None
        )


class ProfileLanguageMixin:
    """Shared get_language for profile serializers."""

    def get_language(self, obj):
        return [
            {"id": str(l.id), "name": l.name, "code": l.code}
            for l in obj.language.all()
        ]


class ProfileUpdateTimestampMixin:
    """Sets updated_at = now() before calling super().update()."""

    def update(self, instance, validated_data):
        instance.updated_at = now()
        return super().update(instance, validated_data)


class ProfileLanguageSaveMixin:
    """Handles language ManyToMany in create/update for Upsert serializers."""

    def update(self, instance, validated_data):
        language = validated_data.pop("language", None)
        instance = super().update(instance, validated_data)
        if language is not None:
            instance.language.set(language)
        return instance

    def create(self, validated_data):
        language = validated_data.pop("language", None)
        instance = super().create(validated_data)
        if language is not None:
            instance.language.set(language)
        return instance


class ProfileLanguageSaveWithTimeMixin(
    ProfileUpdateTimestampMixin, ProfileLanguageSaveMixin
):
    """Save + language M2M; sets updated_at before super().update()."""


class OtpEmailValidationMixin:
    def validate(self, data):
        email = data["email"]
        from user.models import User

        query = User.objects.filter(email=email).first()
        if query is None:
            raise serializers.ValidationError("User not found")
        if data.get("otp") != str(query.otp):
            raise serializers.ValidationError("OTP is incorrect")
        return data
