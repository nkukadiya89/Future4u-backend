from django.db import models

from common.models import BaseModule


class BaseModel(BaseModule):
    """
    Shared abstract model for masters using active/archive flags.
    Inherits audit + soft-delete audit behavior from BaseModule.
    """

    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        abstract = True

