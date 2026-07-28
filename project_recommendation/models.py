from django.db import models


class ProjectRecommendationPanel(models.Model):
    """Unmanaged proxy for AI project recommendation tooling in Django admin."""

    class Meta:
        app_label = "project_recommendation"
        managed = False
        verbose_name = "AI Project Recommendation"
        verbose_name_plural = "AI Project Recommendation"
