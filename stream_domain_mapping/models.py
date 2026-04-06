import uuid

from django.conf import settings
from django.db import models

from base.models import BaseMappingModel


class StreamDomainMapping(BaseMappingModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stream = models.ForeignKey(
        "stream.Stream",
        on_delete=models.CASCADE,
        related_name="stream_domain_mappings",
    )
    domain = models.ForeignKey(
        "domain.Domain",
        on_delete=models.CASCADE,
        related_name="stream_domain_mappings",
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "stream_domain_mapping"
        constraints = [
            models.UniqueConstraint(
                fields=["stream", "domain"],
                name="stream_domain_mapping_stream_domain_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(weight_score__gte=0)
                & models.Q(weight_score__lte=100),
                name="stream_domain_mapping_weight_score_0_100_ck",
            ),
        ]
        indexes = [
            models.Index(fields=["stream"]),
            models.Index(fields=["domain"]),
            models.Index(fields=["weight_score"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["deleted"]),
        ]
        ordering = ["-weight_score", "id"]

    def __str__(self):
        stream_name = getattr(self.stream, "stream_name", None) or str(self.stream_id)
        domain_name = getattr(self.domain, "domain_name", None) or str(self.domain_id)
        return f"{stream_name} -> {domain_name}"


class StreamDomainMappingImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stream_domain_mapping_import_batches",
    )
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "stream_domain_mapping_import_batch"
        ordering = ["-created_at"]


class StreamDomainMappingImportError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        StreamDomainMappingImportBatch,
        on_delete=models.CASCADE,
        related_name="error_rows",
    )
    row_number = models.PositiveIntegerField()
    message = models.CharField(max_length=500)
    row_data = models.JSONField(default=dict)

    class Meta:
        db_table = "stream_domain_mapping_import_error"
        ordering = ["batch", "row_number"]
