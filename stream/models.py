import uuid

from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower

from common.models import BaseModule


class Stream(BaseModule):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stream_code = models.CharField(max_length=64)
    stream_name = models.CharField(max_length=255)
    sequence_order = models.PositiveIntegerField(unique=True)
    parent_safe_label = models.BooleanField(default=False)
    traditional_equivalent = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    education_level = models.ForeignKey(
        "education_level.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="streams",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "stream"
        constraints = [
            UniqueConstraint(
                Lower("stream_code"),
                name="stream_stream_code_ci_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["stream_code"]),
            models.Index(fields=["sequence_order"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["deleted"]),
        ]
        ordering = ["sequence_order", "stream_name"]

    def __str__(self):
        return self.stream_name


class StreamImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stream_import_batches",
    )
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "stream_import_batch"
        ordering = ["-created_at"]


class StreamImportError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        StreamImportBatch,
        on_delete=models.CASCADE,
        related_name="error_rows",
    )
    row_number = models.PositiveIntegerField()
    message = models.CharField(max_length=500)
    row_data = models.JSONField(default=dict)

    class Meta:
        db_table = "stream_import_error"
        ordering = ["batch", "row_number"]
