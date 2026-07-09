from django.db import models


class JobGenerationPanel(models.Model):
    """Unmanaged proxy for AI job generation tooling in Django admin."""

    class Meta:
        app_label = "job_generation"
        managed = False
        verbose_name = "AI Job Generation"
        verbose_name_plural = "AI Job Generation"
