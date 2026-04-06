import uuid

from django.conf import settings
from django.db import models

from base.models import BaseMappingModel


class DomainSkillMapping(BaseMappingModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.ForeignKey(
        "domain.Domain",
        on_delete=models.CASCADE,
        related_name="domain_skill_mappings",
    )
    skill = models.ForeignKey(
        "skill.Skill",
        on_delete=models.CASCADE,
        related_name="domain_skill_mappings",
    )
    is_core = models.BooleanField(default=False)

    class Meta:
        db_table = "domain_skill_mapping"
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "skill"],
                name="domain_skill_mapping_domain_skill_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(weight_score__gte=0)
                & models.Q(weight_score__lte=100),
                name="domain_skill_mapping_weight_score_0_100_ck",
            ),
        ]
        indexes = [
            models.Index(fields=["domain"]),
            models.Index(fields=["skill"]),
            models.Index(fields=["weight_score"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["deleted"]),
        ]
        ordering = ["-weight_score", "id"]

    def __str__(self):
        domain_name = getattr(self.domain, "domain_name", None) or str(self.domain_id)
        skill_name = getattr(self.skill, "skill_name", None) or str(self.skill_id)
        return f"{domain_name} -> {skill_name}"


class DomainSkillMappingImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="domain_skill_mapping_import_batches",
    )
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "domain_skill_mapping_import_batch"
        ordering = ["-created_at"]


class DomainSkillMappingImportError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        DomainSkillMappingImportBatch,
        on_delete=models.CASCADE,
        related_name="error_rows",
    )
    row_number = models.PositiveIntegerField()
    message = models.CharField(max_length=500)
    row_data = models.JSONField(default=dict)

    class Meta:
        db_table = "domain_skill_mapping_import_error"
        ordering = ["batch", "row_number"]
