"""Resume Builder models — Path B (JSON Resume) persistence layer.

- GeneratedResume stores every AI-generated canonical JSON Resume (full history).
- ResumeTemplate is the backend template registry (presentation metadata only;
  the actual frontend themes live on the frontend).
"""

from django.conf import settings
from django.db import models

from common.models import BaseModule


class GeneratedResume(BaseModule):
    """One AI-generated canonical JSON Resume per row (history preserved)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_resumes",
    )
    template = models.CharField(max_length=100, help_text="Registered template code")
    resume_json = models.JSONField(help_text="Canonical JSON Resume object")
    tokens_used = models.PositiveIntegerField(default=0)
    resume_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="fresher | professional | child",
    )

    class Meta:
        db_table = "generated_resume"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "template"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"GeneratedResume<{self.id} user={self.user_id} template={self.template}>"


class ResumeTemplate(BaseModule):
    """Backend registry of allowed resume template codes."""

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    preview_image = models.URLField(blank=True)
    category = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "resume_template"
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} ({self.name})"
