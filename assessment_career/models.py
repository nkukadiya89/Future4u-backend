from django.conf import settings
from django.db import models

from common.models import BaseModule


class CareerRecommendation(BaseModule):

    class ProfileType(models.TextChoices):
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent"
        PROFESSIONAL = "working_professional", "Working Professional"

    profile_type = models.CharField(
        max_length=30,
        choices=ProfileType.choices,
        default="student",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="career_recommendations",
        db_index=True,
    )
    student_assessment = models.OneToOneField(
        "assessment.StudentAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="career_recommendation",
    )
    parent_assessment = models.OneToOneField(
        "assessment.ParentAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="career_recommendation",
    )
    professional_assessment = models.OneToOneField(
        "assessment.ProfessionalAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="career_recommendation",
    )
    raw_ai_response = models.JSONField(default=dict, blank=True)
    easy_decision_making = models.JSONField(default=list, blank=True)
    last_recommended_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "career_recommendation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Rec {self.id} ({self.profile_type})"

    @property
    def assessment(self):
        return (
            self.student_assessment
            or self.parent_assessment
            or self.professional_assessment
        )


class CareerSuggestion(BaseModule):

    recommendation = models.ForeignKey(
        CareerRecommendation,
        on_delete=models.CASCADE,
        related_name="suggestions",
        db_index=True,
    )
    career_name = models.CharField(max_length=250, null=True, blank=True)
    match_percentage = models.PositiveIntegerField()
    ai_insight = models.TextField()
    why_this_career = models.JSONField(default=list, blank=True)
    required_skills = models.JSONField(default=list, blank=True)
    required_education = models.JSONField(default=dict, blank=True)
    career_factors = models.JSONField(default=dict, blank=True)
    career_roadmap = models.JSONField(default=dict, blank=True)
    display_order = models.PositiveIntegerField(default=1, db_index=True)

    class Meta:
        db_table = "career_suggestion"
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.career_name


class ChatSession(BaseModule):

    suggestion = models.OneToOneField(
        CareerSuggestion,
        on_delete=models.CASCADE,
        related_name="chat_session",
    )
    child = models.ForeignKey(
        "user_profile.ChildProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_sessions",
        help_text="The child this chat session is about (for parent profile chats).",
    )
    summary = models.TextField(blank=True, default="")

    class Meta:
        db_table = "career_chat_session"

    def __str__(self):
        return f"Chat for {self.suggestion_id}"


class ChatMessage(BaseModule):

    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_CHOICES = (
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
    )

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()

    class Meta:
        db_table = "career_chat_message"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"
