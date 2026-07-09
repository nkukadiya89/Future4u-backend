from django.db import models


class InternshipGenerationPanel(models.Model):
    """Unmanaged proxy for AI internship generation tooling in Django admin."""

    class Meta:
        app_label = "internship_generation"
        managed = False
        verbose_name = "AI Internship Generation"
        verbose_name_plural = "AI Internship Generation"
