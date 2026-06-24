from django.db import models
from common.models import BaseModule
from django.conf import settings

class CareerRecommendation(BaseModule):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="career_recommendation", null=True,blank=True,db_index=True)
    assessment = models.OneToOneField("assessment.StudentAssessment", on_delete=models.CASCADE, related_name="career_recommendation", null=True, blank=True)
    raw_ai_response = models.JSONField(default=dict, blank=True)
    easy_decision_making = models.JSONField(default=list, blank=True)
    last_recommended_at = models.DateTimeField(null=True, blank=True,db_index=True)

    class Meta:
        db_table = "career_recommendation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Recommendation {self.id}"

class CareerRecommendationSuggestion(BaseModule):
    recommendation = models.ForeignKey(CareerRecommendation, on_delete=models.CASCADE, related_name="suggestions",db_index=True)
    career_name = models.CharField(max_length=250, null=True, blank=True)
    match_percentage = models.PositiveIntegerField()
    ai_insight = models.TextField()
    why_this_career = models.JSONField(default=list, blank=True)
    required_skills = models.JSONField(default=list, blank=True)
    required_education = models.JSONField(default=dict, blank=True)
    career_factors = models.JSONField(default=list, blank=True)
    career_roadmap = models.JSONField(default=dict, blank=True)
    display_order = models.PositiveIntegerField(default=1, db_index=True)
    
    class Meta:
        db_table = "career_recommendation_suggestion"
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.career_name


class CareerRecommendationChatSession(BaseModule):
    suggestion = models.OneToOneField(
        CareerRecommendationSuggestion,
        on_delete=models.CASCADE,
        related_name="chat_session",
    )
    summary = models.TextField(blank=True, default="")

    class Meta:
        db_table = "career_recommendation_chat_session"

    def __str__(self):
        return f"Chat for {self.suggestion_id}"


class CareerRecommendationChatMessage(BaseModule):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_CHOICES = (
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
    )

    session = models.ForeignKey(
        CareerRecommendationChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()

    class Meta:
        db_table = "career_recommendation_chat_message"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"


class ParentCareerRecommendation(BaseModule):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parent_career_recommendation",
        null=True, blank=True,
        db_index=True,
    )
    assessment = models.OneToOneField(
        "assessment.ParentAssessment",
        on_delete=models.CASCADE,
        related_name="parent_career_recommendation",
        null=True, blank=True,
    )
    raw_ai_response = models.JSONField(default=dict, blank=True)
    easy_decision_making = models.JSONField(default=list, blank=True)
    last_recommended_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "parent_career_recommendation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ParentRecommendation {self.id}"


class ParentCareerRecommendationSuggestion(BaseModule):
    recommendation = models.ForeignKey(
        ParentCareerRecommendation,
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
    career_factors = models.JSONField(default=list, blank=True)
    career_roadmap = models.JSONField(default=dict, blank=True)
    display_order = models.PositiveIntegerField(default=1, db_index=True)

    class Meta:
        db_table = "parent_career_recommendation_suggestion"
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.career_name


class ParentCareerRecommendationChatSession(BaseModule):
    suggestion = models.OneToOneField(
        ParentCareerRecommendationSuggestion,
        on_delete=models.CASCADE,
        related_name="chat_session",
    )
    summary = models.TextField(blank=True, default="")

    class Meta:
        db_table = "parent_career_recommendation_chat_session"

    def __str__(self):
        return f"Chat for {self.suggestion_id}"


class ParentCareerRecommendationChatMessage(BaseModule):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_CHOICES = (
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
    )

    session = models.ForeignKey(
        ParentCareerRecommendationChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()

    class Meta:
        db_table = "parent_career_recommendation_chat_message"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"
