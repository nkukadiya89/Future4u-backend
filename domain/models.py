import uuid
import os

from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower

from base.models import MasterBaseModel
from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket


class Domain(MasterBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain_code = models.CharField(max_length=64)
    domain_name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_domains",
    )
    description = models.TextField(blank=True)
    domain_image = models.CharField(
        max_length=250, null=True, blank=True, help_text="Upload domain image/icon"
    )

    class Meta:
        db_table = "domain"
        constraints = [
            UniqueConstraint(
                Lower("domain_code"),
                name="domain_domain_code_ci_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["domain_code"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["deleted"]),
        ]

    def __str__(self):
        return f"{self.domain_code} - {self.domain_name}"

    def upload_domain_image(self, domain_image_file):
        """Upload domain image to AWS S3 following the same pattern as User model"""
        allowed_types = [".jpg", ".jpeg", ".png"]

        file_extension = os.path.splitext(domain_image_file.name)[1].lower()
        if file_extension not in allowed_types:
            raise ValueError(
                f"Invalid file type: {file_extension}. Allowed types are {', '.join(allowed_types)}."
            )

        current_value = getattr(self, "domain_image", None)

        try:
            if current_value:
                delete_uploaded_file(current_value)

            aws_file_url, presigned_url = upload_file_to_bucket(
                domain_image_file,
                allowed_types,
                "DomainImages/",
                str(self.id),
                None,
            )
            self.domain_image = aws_file_url
            self.save(update_fields=["domain_image"])
            return aws_file_url
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to upload domain image: {str(e)}")


class DomainImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="domain_import_batches",
    )
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "domain_import_batch"
        ordering = ["-created_at"]


class DomainImportError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        DomainImportBatch,
        on_delete=models.CASCADE,
        related_name="error_rows",
    )
    row_number = models.PositiveIntegerField()
    message = models.CharField(max_length=500)
    row_data = models.JSONField(default=dict)

    class Meta:
        db_table = "domain_import_error"
        ordering = ["batch", "row_number"]
