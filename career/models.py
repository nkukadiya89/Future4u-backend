import uuid

from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower

from base.models import MasterBaseModel


class Career(MasterBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    career_code = models.CharField(max_length=64)
    career_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    min_education_level = models.ForeignKey(
        "education_level.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="careers_min_level",
    )
    max_education_level = models.ForeignKey(
        "education_level.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="careers_max_level",
    )

    class Meta:
        db_table = "career"
        constraints = [
            UniqueConstraint(
                Lower("career_code"),
                name="career_career_code_ci_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["career_code"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["deleted"]),
        ]

    def __str__(self):
        return self.career_name


class CareerImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="career_import_batches",
    )
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "career_import_batch"
        ordering = ["-created_at"]


class CareerImportError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        CareerImportBatch,
        on_delete=models.CASCADE,
        related_name="error_rows",
    )
    row_number = models.PositiveIntegerField()
    message = models.CharField(max_length=500)
    row_data = models.JSONField(default=dict)

    class Meta:
        db_table = "career_import_error"
        ordering = ["batch", "row_number"]
