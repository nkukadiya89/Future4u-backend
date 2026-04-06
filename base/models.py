from django.db import models

from common.models import BaseModule
from django.utils import timezone


class MasterBaseModel(BaseModule):
    """
    Shared abstract base for "master" tables.

    - Keeps `BaseModule` as the source of truth for archive/soft-delete via `deleted`.
    - Adds `is_active` for master-table enable/disable behavior.
    """

    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class BaseModel(BaseModule):
    """
    Shared abstract base model for production modules.

    Intentionally composes `common.models.BaseModule` (existing audit + soft delete)
    to avoid schema duplication and preserve legacy behavior.
    """

    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def restore(self, *, user=None):
        self.deleted = False
        if hasattr(self, "deleted_at"):
            self.deleted_at = None
        if hasattr(self, "deleted_by"):
            self.deleted_by = None
        self.updated_at = timezone.now()
        if user is not None:
            self.updated_by = user
        self.save(
            user=user,
            update_fields=[
                "deleted",
                "deleted_at",
                "deleted_by",
                "updated_at",
                "updated_by",
            ],
        )
        return self


class BaseMappingModel(BaseModel):
    """
    Abstract base for mapping/link tables.
    """

    weight_score = models.PositiveSmallIntegerField()

    class Meta:
        abstract = True
