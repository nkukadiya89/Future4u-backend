from django.db import models


class AIRecommendationPanel(models.Model):
    """Unmanaged proxy — hooks AI recommendation tooling into Django admin."""

    class Meta:
        app_label = "recommendation"
        managed = False
        verbose_name = "AI Recommendations"
        verbose_name_plural = "AI Recommendations"
