from django.utils import timezone


def soft_delete(instance, *, user=None, archive_field="is_archived"):
    setattr(instance, archive_field, True)
    _save_instance(instance, user=user)
    return instance


def restore(instance, *, user=None, archive_field="is_archived"):
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

