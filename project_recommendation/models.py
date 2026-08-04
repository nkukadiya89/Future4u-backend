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

    One row per assessment (upserted on regeneration). Metadata lives in
    columns; the full AI payload (projects list) is stored in
    `raw_ai_response` so the exact generated response is always available.
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
    student_assessment = models.OneToOneField(
        "assessment.StudentAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_recommendation",
    )
    parent_assessment = models.OneToOneField(
        "assessment.ParentAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_recommendation",
    )
    professional_assessment = models.OneToOneField(
        "assessment.ProfessionalAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_recommendation",
    )
    domain = models.CharField(max_length=250, blank=True, default="")
    domain_category = models.CharField(max_length=250, blank=True, default="")
    education_level = models.CharField(max_length=150, blank=True, default="")
    raw_ai_response = models.JSONField(default=dict, blank=True)
    token_usage = models.PositiveIntegerField(default=0)
    last_recommended_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "project_recommendation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ProjectRec {self.id} ({self.profile_type})"

    @property
    def assessment(self):
        return (
            self.student_assessment
            or self.parent_assessment
            or self.professional_assessment
        )
