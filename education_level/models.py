import uuid

from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower

from base.models import BaseModel


class EducationLevel(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    level_code = models.CharField(max_length=64)
    display_name = models.CharField(max_length=255)
    sequence_order = models.PositiveIntegerField(unique=True)
    min_age = models.PositiveIntegerField()
    max_age = models.PositiveIntegerField()

    class Meta:
        db_table = "education_level"
        constraints = [
            UniqueConstraint(
                Lower("level_code"),
                name="education_level_level_code_ci_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["level_code"]),
            models.Index(fields=["sequence_order"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_archived"]),
        ]
        ordering = ["sequence_order", "display_name"]

    def __str__(self):
        return self.display_name


class EducationLevelImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="education_level_import_batches",
    )
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "education_level_import_batch"
        ordering = ["-created_at"]


class EducationLevelImportError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        EducationLevelImportBatch,
        on_delete=models.CASCADE,
        related_name="error_rows",
    )
    row_number = models.PositiveIntegerField()
    message = models.CharField(max_length=500)
    row_data = models.JSONField(default=dict)

    class Meta:
        db_table = "education_level_import_error"
        ordering = ["batch", "row_number"]
