from django.utils import timezone


def soft_delete(instance, *, user=None, archive_field="deleted"):
    """
    Project convention: "archived" == soft-deleted via BaseModule.deleted (+ deleted_at/by).
    Kept generic for legacy callers via archive_field, but defaults to the source of truth.
    """
    if archive_field == "deleted" and hasattr(instance, "soft_delete"):
        instance.soft_delete(user=user)
        return instance
    setattr(instance, archive_field, True)
    _save_instance(instance, user=user)
    return instance


def restore(instance, *, user=None, archive_field="deleted"):
    if archive_field == "deleted":
        setattr(instance, "deleted", False)
        if hasattr(instance, "deleted_at"):
            setattr(instance, "deleted_at", None)
        if hasattr(instance, "deleted_by"):
            setattr(instance, "deleted_by", None)
        if hasattr(instance, "updated_at"):
            instance.updated_at = timezone.now()
        if user is not None and hasattr(instance, "updated_by"):
            instance.updated_by = user
        _save_instance(instance, user=user)
        return instance
    setattr(instance, archive_field, False)
    _save_instance(instance, user=user)
    return instance


def toggle_status(instance, *, user=None, status_field="is_active"):
    current = bool(getattr(instance, status_field, False))
    setattr(instance, status_field, not current)
    _save_instance(instance, user=user)
    return instance


def _save_instance(instance, *, user=None):
    if user is not None:
        try:
            instance.save(user=user)
            return
        except TypeError:
            pass
    instance.updated_at = timezone.now()
    instance.save()


class BaseService:
    @staticmethod
    def soft_delete(instance, *, user=None):
        return soft_delete(instance, user=user, archive_field="deleted")

    @staticmethod
    def restore(instance, *, user=None):
        return restore(instance, user=user, archive_field="deleted")

    @staticmethod
    def validate_weight(value):
        if value is None:
            return
        try:
            v = int(value)
        except (TypeError, ValueError):
            raise ValueError("Invalid weight_score")
        if v < 0 or v > 100:
            raise ValueError("weight_score must be between 0 and 100")

    @staticmethod
    def validate_unique_pair(queryset, filters: dict, *, exclude_pk=None):
        q = queryset.filter(**filters)
        if exclude_pk is not None:
            q = q.exclude(pk=exclude_pk)
        if q.exists():
            try:
                from rest_framework.exceptions import ValidationError

                raise ValidationError("Duplicate mapping.")
            except Exception:
                raise ValueError("Duplicate mapping.")
