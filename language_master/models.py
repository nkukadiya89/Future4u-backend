import uuid

from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower

from base.models import MasterBaseModel


class Language(MasterBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="e.g. English, Hindi, Gujarati")
    code = models.CharField(max_length=10, help_text="e.g. EN, HI, GU")
    description = models.TextField(blank=True)

    class Meta:
        db_table = "language_master"
        constraints = [
            UniqueConstraint(
                Lower("code"),
                name="language_master_code_ci_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["deleted"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class LanguageImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="language_import_batches",
    )
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "language_import_batch"
        ordering = ["-created_at"]


class LanguageImportError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        LanguageImportBatch,
        on_delete=models.CASCADE,
        related_name="error_rows",
    )
    row_number = models.PositiveIntegerField()
    message = models.CharField(max_length=500)
    row_data = models.JSONField(default=dict)

    class Meta:
        db_table = "language_import_error"
        ordering = ["batch", "row_number"]
