from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import BaseModule


class Question(models.Model):
    class Dimension(models.TextChoices):
        BACKGROUND = "background", "Background"
        INTEREST = "interest", "Interest"
        ACADEMIC_STRENGTH = "academic_strength", "Academic Strength"
        SKILL_CONFIDENCE = "skill_confidence", "Skill Confidence"
        EXPOSURE = "exposure", "Exposure"
        WORK_PREFERENCE = "work_preference", "Work Preference"
        READINESS = "readiness", "Readiness"
        APTITUDE = "aptitude", "Aptitude"
        PERSONALITY = "personality", "Personality"
        WORK_STYLE = "work_style", "Work Style"

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
        help_text="Display order within the same education level and signal type.",
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


class UserResponse(models.Model):
    assessment = models.ForeignKey(
        "assessment.StudentAssessment",
        on_delete=models.CASCADE,
        related_name="responses",
        null=True,
        blank=True,
    )
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
                fields=["assessment", "question"],
                name="assessment_question_unique",
            ),
        ]

    def __str__(self):
        return f"user={self.user_id}, question={self.question_id}, score={self.score_value}"

class StudentAssessment(BaseModule):
    class Screen(models.TextChoices):
        EDUCATION_LEVEL = "education_level", "Education Level"
        STREAM = "stream", "Stream / Path"
        DOMAIN_CATEGORY = "domain_category", "Domain Category"
        DOMAIN = "domain", "Domain"
        CAREER_DIRECTION = "career_direction", "Career Direction"
        PARENT_SUPPORT = "parent_support", "Parent Support"
        CONCERNS = "concerns", "Concerns"
        QUESTIONS = "questions", "Dynamic Questions"
        CAREER_VALUES = "career_values", "Career Values"
        USER_GOALS = "user_goals", "User Goals"
        COMPLETE = "complete", "Complete"

    PARENT_CHOICES = (
        ("very_supportive", "Very Supportive"),
        ("somewhat_supportive", "SomeWhat Supportive"),
        ("neutral", "Neutral"),
        ("not_supportive", "Not Supportive"),
        ("notsure", "Not Sure"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_assessments",
    )
    domain_category = models.ForeignKey(
        "domain.Domain",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="category_assessments",
        help_text="Parent category domain selected by the student.",
    )
    domain = models.ForeignKey(
        "domain.Domain",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessments",
        help_text="Child domain selected by the student.",
    )
    career_direction = models.JSONField(default=list, blank=True, null=True)
    parent_support = models.CharField(choices=PARENT_CHOICES, max_length=150, null=True, blank=True)
    concerns = models.JSONField(default=list, blank=True, null=True)
    career_values = models.JSONField(default=list, blank=True, null=True)
    user_goals = models.JSONField(default=list, blank=True, null=True)
    current_screen = models.CharField(
        max_length=32,
        choices=Screen.choices,
        default=Screen.EDUCATION_LEVEL,
    )
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = "student_assessment"
        ordering = ["-created_at"]
    def __str__(self):
        return f"Assessment {self.id} - User {self.user_id}"
    
