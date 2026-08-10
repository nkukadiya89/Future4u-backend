from django.db import models


class CourseGenerationPanel(models.Model):
    """Unmanaged proxy for AI course generation tooling in Django admin."""

    class Meta:
        app_label = "course_generation"
        managed = False
        verbose_name = "AI Course Generation"
        verbose_name_plural = "AI Course Generation"
        permissions = [
            ("generate_course", "Can generate AI course details"),
        ]
