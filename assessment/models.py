from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Question(models.Model):
    class Dimension(models.TextChoices):
        INTEREST = "interest", "Interest"
        APTITUDE = "aptitude", "Aptitude"
        PERSONALITY = "personality", "Personality"
        WORK_STYLE = "work_style", "Work Style"

    question_text = models.TextField()
    dimension = models.CharField(max_length=20, choices=Dimension.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "assessment_question"
        ordering = ["id"]

    def __str__(self):
        return f"{self.dimension}: {self.question_text[:60]}"


class Option(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_text = models.CharField(max_length=255)
    score_value = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        db_table = "assessment_option"
        ordering = ["id"]

    def __str__(self):
        return f"Q{self.question_id} - {self.option_text[:40]}"


class UserResponse(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_responses",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    selected_option = models.ForeignKey(
        Option,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    score_value = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        db_table = "assessment_user_response"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question"],
                name="assessment_user_question_unique",
            ),
        ]

    def __str__(self):
        return f"user={self.user_id}, question={self.question_id}, score={self.score_value}"
