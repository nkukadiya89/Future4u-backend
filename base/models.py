from django.db import models

from common.models import BaseModule


class MasterBaseModel(BaseModule):
    """
    Shared abstract base for "master" tables.

    - Keeps `BaseModule` as the source of truth for archive/soft-delete via `deleted`.
    - Adds `is_active` for master-table enable/disable behavior.
    """

    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

