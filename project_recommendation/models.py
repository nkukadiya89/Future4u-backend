from django.conf import settings
from django.db import models

from common.models import BaseModule


class ProjectRecommendationPanel(models.Model):
    """Unmanaged proxy for AI project recommendation tooling in Django admin."""

    class Meta:
        app_label = "project_recommendation"
        managed = False
        verbose_name = "AI Project Recommendation"
        verbose_name_plural = "AI Project Recommendation"


class ProjectRecommendation(BaseModule):
    """Persists the full AI-generated project recommendation response.

    Fully standalone — not linked to any assessment or career
    recommendation. Generated from domain + domain category dropdowns and
    an optional overview text. One row per (profile_type, domain,
    domain_category, overview) input, upserted on regeneration. The full
    response payload (projects list) is stored in `raw_ai_response` so the
    exact served response is always available (LLM-generated,
    token_usage > 0).
    """

    class ProfileType(models.TextChoices):
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent"
        PROFESSIONAL = "working_professional", "Working Professional"
 
    profile_type = models.CharField(
        max_length=30,
        choices=ProfileType.choices,
        default=ProfileType.STUDENT,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_recommendations",
        db_index=True,
    )
    domain = models.CharField(max_length=250, blank=True, default="")
    domain_category = models.CharField(max_length=250, blank=True, default="")
    overview = models.TextField(blank=True, default="")
    raw_ai_response = models.JSONField(default=dict, blank=True)
    token_usage = models.PositiveIntegerField(default=0)
    last_recommended_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "project_recommendation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ProjectRec {self.id} ({self.profile_type})"


