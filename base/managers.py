from django.db import models


class BaseQuerySet(models.QuerySet):
    """
    Utility queryset helpers.

    IMPORTANT: does not override global default filtering.
    """

    def active(self):
        return self.filter(is_active=True, deleted=False)

    def deleted(self):
        return self.filter(deleted=True)


class BaseManager(models.Manager.from_queryset(BaseQuerySet)):
    """
    Opt-in manager for models that want `.active()` / `.deleted_only()`.
    """

    pass

