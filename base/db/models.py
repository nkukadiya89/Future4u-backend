from django.db import models
from django.utils.timezone import now


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True
