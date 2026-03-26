import uuid

from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower

from base.models import MasterBaseModel


class SkillType(models.TextChoices):
    TECHNICAL = "technical", "Technical"
    SOFT = "soft", "Soft"
    ANALYTICAL = "analytical", "Analytical"
    CREATIVE = "creative", "Creative"


class Skill(MasterBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    skill_code = models.CharField(max_length=64)
    skill_name = models.CharField(max_length=255)
    skill_type = models.CharField(max_length=32, choices=SkillType.choices)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "skill"
        constraints = [
            UniqueConstraint(
                Lower("skill_code"),
                name="skill_skill_code_ci_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["skill_code"]),
            models.Index(fields=["skill_type"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["deleted"]),
        ]

    def __str__(self):
        return self.skill_name


class SkillImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="skill_import_batches",
    )
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "skill_import_batch"
        ordering = ["-created_at"]


class SkillImportError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        SkillImportBatch,
        on_delete=models.CASCADE,
        related_name="error_rows",
    )
    row_number = models.PositiveIntegerField()
    message = models.CharField(max_length=500)
    row_data = models.JSONField(default=dict)

    class Meta:
        db_table = "skill_import_error"
        ordering = ["batch", "row_number"]

