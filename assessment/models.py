import os

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from common.models import BaseModule
from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket


class AssessmentInterestCategory(BaseModule):
    category_code = models.CharField(max_length=64, unique=True)
    category_name = models.CharField(max_length=255, unique=True)
    category_image_url = models.CharField(max_length=500, null=True, blank=True)
    sequence_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.category_name

    def upload_category_image(self, category_image_file):
        allowed_types = [".jpg", ".jpeg", ".png"]

        file_extension = os.path.splitext(category_image_file.name)[1].lower()
        if file_extension not in allowed_types:
            raise ValueError(
                f"Invalid file type: {file_extension}. Allowed types are {', '.join(allowed_types)}."
            )

        current_value = getattr(self, "category_image_url", None)

        try:
            if current_value:
                delete_uploaded_file(current_value)

            aws_file_url, _ = upload_file_to_bucket(
                category_image_file,
                allowed_types,
                "AssessmentInterestCategory/",
                self.id,
                None,
            )
            self.category_image_url = aws_file_url
            self.save(update_fields=["category_image_url"])
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to upload category image: {str(e)}")

    class Meta:
        db_table = "assessment_interest_category"
        ordering = ["sequence_order", "category_name"]


class Question(models.Model):
    class Dimension(models.TextChoices):
        INTEREST = "interest", "Interest"
        APTITUDE = "aptitude", "Aptitude"
        PERSONALITY = "personality", "Personality"
        WORK_STYLE = "work_style", "Work Style"
        BACKGROUND = "background", "Background"  # warmup / context questions

    class QuestionType(models.TextChoices):
        SCALE = "scale", "Scale (1-5 agreement)"
        MCQ = "mcq", "Multiple Choice (pick one)"
        YESNO = "yesno", "Yes / No"

    question_text = models.TextField()
    dimension = models.CharField(max_length=20, choices=Dimension.choices)
    question_type = models.CharField(
        max_length=10,
        choices=QuestionType.choices,
        default=QuestionType.SCALE,
        help_text="Controls how options are presented to the user.",
    )
    sequence_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display order within the same education level and dimension.",
    )
    mapped_domains = models.ManyToManyField(
        "domain.Domain",
        related_name="assessment_questions",
        blank=True,
    )
    signal_strength = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    # Education-level aware filtering
    education_level = models.ForeignKey(
        "education_level.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessment_questions",
        help_text="If set, this question is only shown to users at this education level.",
    )
    # For 12th-grade users: optionally restrict question to a specific stream
    target_stream = models.ForeignKey(
        "stream.Stream",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessment_questions",
        db_column="stream_id",
        help_text="If set, this question is only shown to 12th-grade users who selected this stream.",
    )
    # For 10th-grade users: which streams does a positive answer signal?
    mapped_streams = models.ManyToManyField(
        "stream.Stream",
        related_name="signal_questions",
        blank=True,
        help_text="Streams this question signals affinity for (used for 10th-grade stream recommendations).",
    )

    class Meta:
        db_table = "assessment_question"
        ordering = ["education_level", "sequence_order", "id"]

    def __str__(self):
        return f"[{self.dimension}] {self.question_text[:60]}"


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
    sequence_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display order of this option within its question.",
    )

    class Meta:
        db_table = "assessment_option"
        ordering = ["sequence_order", "id"]

    def __str__(self):
        return f"Q{self.question_id} - {self.option_text[:40]}"


class AssessmentAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_attempts",
    )
    attempt_number = models.PositiveSmallIntegerField()
    domain_interests = models.ManyToManyField(
        AssessmentInterestCategory,
        blank=True,
        related_name="assessment_attempts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "assessment_attempt"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"user={self.user_id}, attempt={self.attempt_number}"


class UserResponse(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_responses",
    )
    attempt = models.ForeignKey(
        AssessmentAttempt,
        on_delete=models.CASCADE,
        related_name="responses",
        null=True,
        blank=True,
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
                fields=["attempt", "question"],
                name="assessment_attempt_question_unique",
            ),
        ]

    def __str__(self):
        return f"user={self.user_id}, question={self.question_id}, score={self.score_value}"
