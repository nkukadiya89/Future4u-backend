import uuid
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower

from base.models import MasterBaseModel
from utils.aws_file_upload import upload_file_to_bucket


class Domain(MasterBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain_code = models.CharField(max_length=64)
    domain_name = models.CharField(max_length=255)
    domain_category = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="Broad category e.g. healthcare, technology, government, creative_arts",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_domains",
    )
    parent_acceptance_level = models.PositiveSmallIntegerField()
    future_relevance_score = models.PositiveSmallIntegerField()
    description = models.TextField(blank=True)
    domain_image = models.ImageField(
        upload_to='domain_images/',
        blank=True,
        null=True,
        help_text="Upload domain image/icon"
    )

    # How much each assessment dimension contributes to this domain's fit score.
    # Nullable to allow "use default/fallback" behavior.
    interest_weight = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    aptitude_weight = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    personality_weight = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    work_style_weight = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
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

    def clean(self):
        """
        Validation for dimension affinity weights:
        - either all 4 weights are null (meaning: fallback weights will be used), OR all 4 are provided
        - each weight must be in [0, 1] (field validators)
        - sum must be ~1.0 when provided
        """
        super().clean()
        fields = (
            "interest_weight",
            "aptitude_weight",
            "personality_weight",
            "work_style_weight",
        )
        values = [getattr(self, f) for f in fields]
        provided = [v for v in values if v is not None]
        if not provided:
            return
        if len(provided) != 4:
            raise ValidationError(
                {f: "Provide all 4 weights, or leave all blank." for f in fields}
            )
        total = float(sum(provided))
        if abs(total - 1.0) > 0.001:
            raise ValidationError({f: "Weights must sum to 1.0." for f in fields})

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
                # Note: You may want to implement delete_uploaded_file for domain images too
                pass
            
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


class DomainReportMeta(models.Model):
    """
    Student-facing report data per domain (degrees, careers, note, how_to_choose_hint).
    Loaded via: python manage.py init_domain_report_meta
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain_code = models.CharField(max_length=64, unique=True, db_index=True)
    degrees = models.TextField(blank=True, help_text="Pipe-separated degree options")
    careers = models.TextField(blank=True, help_text="Pipe-separated career titles")
    note = models.CharField(max_length=512, blank=True)
    direction_why = models.TextField(
        blank=True, help_text="One-liner: why this field suits the user"
    )
    how_to_choose_hint = models.CharField(max_length=512, blank=True)
    next_step_1 = models.TextField(blank=True)
    next_step_2 = models.TextField(blank=True)
    next_step_3 = models.TextField(blank=True)

    class Meta:
        db_table = "domain_report_meta"

    def __str__(self):
        return self.domain_code

    def degrees_list(self) -> list:
        return [d.strip() for d in self.degrees.split("|") if d.strip()]

    def careers_list(self) -> list:
        return [c.strip() for c in self.careers.split("|") if c.strip()]

    def next_steps(self) -> list:
        return [
            s
            for s in [self.next_step_1, self.next_step_2, self.next_step_3]
            if s.strip()
        ]


class DomainCounsellorKnowledge(models.Model):
    """
    Counsellor message content per domain (insight, tradeoff, action, tension).
    Loaded via: python manage.py init_domain_counsellor_knowledge
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain_code = models.CharField(max_length=64, unique=True, db_index=True)
    insight = models.TextField(blank=True)
    tradeoff = models.TextField(blank=True)
    action = models.TextField(blank=True)
    tension = models.TextField(blank=True)
    technical_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="Technical skill keywords for this domain e.g. ['python','sql','machine learning']",
    )
    domain_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="Domain/soft skill keywords for this domain e.g. ['data analysis','research']",
    )

    class Meta:
        db_table = "domain_counsellor_knowledge"

    def __str__(self):
        return self.domain_code

    def as_tuple(self) -> tuple:
        return (self.insight, self.tradeoff, self.action, self.tension)


class StreamCounsellorKnowledge(models.Model):
    """
    Counsellor message content per stream (insight, tradeoff, action, tension).
    Loaded via: python manage.py init_stream_counsellor_knowledge
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stream_code = models.CharField(max_length=64, unique=True, db_index=True)
    insight = models.TextField(blank=True)
    tradeoff = models.TextField(blank=True)
    action = models.TextField(blank=True)
    tension = models.TextField(blank=True)

    class Meta:
        db_table = "stream_counsellor_knowledge"

    def __str__(self):
        return self.stream_code

    def as_tuple(self) -> tuple:
        return (self.insight, self.tradeoff, self.action, self.tension)


class DomainScoringConfig(models.Model):
    """
    DB-driven scoring config per domain (dimensions, careers, rules).
    Loaded via: python manage.py init_data
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain_code = models.CharField(max_length=64, unique=True, db_index=True)
    config = models.JSONField(
        default=dict, help_text="Full scoring config for this domain"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "domain_scoring_config"

    def __str__(self):
        return self.domain_code


class StreamReportMeta(models.Model):
    """
    Student-facing report data per stream (why, subjects, careers, note, next steps).
    Loaded via: python manage.py init_stream_report_meta
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stream_code = models.CharField(max_length=64, unique=True, db_index=True)
    why = models.CharField(
        max_length=512, blank=True, help_text="One-line direction explanation"
    )
    subjects = models.TextField(blank=True, help_text="Pipe-separated subject names")
    careers = models.TextField(blank=True, help_text="Pipe-separated career titles")
    note = models.CharField(
        max_length=512, blank=True, help_text="Day-to-day work description"
    )
    next_step_1 = models.TextField(blank=True)
    next_step_2 = models.TextField(blank=True)
    next_step_3 = models.TextField(blank=True)

    class Meta:
        db_table = "stream_report_meta"

    def __str__(self):
        return self.stream_code

    def subjects_list(self) -> list:
        return [s.strip() for s in self.subjects.split("|") if s.strip()]

    def careers_list(self) -> list:
        return [c.strip() for c in self.careers.split("|") if c.strip()]

    def next_steps(self) -> list:
        return [
            s
            for s in [self.next_step_1, self.next_step_2, self.next_step_3]
            if s.strip()
        ]
