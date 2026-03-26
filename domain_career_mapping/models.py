import uuid

from django.conf import settings
from django.db import models

from common.models import BaseModule


class DomainCareerMapping(BaseModule):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.ForeignKey(
        "domain.Domain",
        on_delete=models.CASCADE,
        related_name="domain_career_mappings",
    )
    career = models.ForeignKey(
        "career.Career",
        on_delete=models.CASCADE,
        related_name="domain_career_mappings",
    )
    weight_score = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "domain_career_mapping"
        constraints = [
            models.UniqueConstraint(fields=["domain", "career"], name="domain_career_mapping_domain_career_uniq"),
            models.CheckConstraint(
                condition=models.Q(weight_score__gte=0) & models.Q(weight_score__lte=100),
                name="domain_career_mapping_weight_score_0_100_ck",
            ),
        ]
        indexes = [
            models.Index(fields=["domain"]),
            models.Index(fields=["career"]),
            models.Index(fields=["weight_score"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["deleted"]),
        ]
        ordering = ["-weight_score", "id"]

    def __str__(self):
        domain_name = getattr(self.domain, "domain_name", None) or str(self.domain_id)
        career_name = getattr(self.career, "career_name", None) or str(self.career_id)
        return f"{domain_name} -> {career_name}"


class DomainCareerMappingImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="domain_career_mapping_import_batches",
    )
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "domain_career_mapping_import_batch"
        ordering = ["-created_at"]


class DomainCareerMappingImportError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        DomainCareerMappingImportBatch,
        on_delete=models.CASCADE,
        related_name="error_rows",
    )
    row_number = models.PositiveIntegerField()
    message = models.CharField(max_length=500)
    row_data = models.JSONField(default=dict)

    class Meta:
        db_table = "domain_career_mapping_import_error"
        ordering = ["batch", "row_number"]

