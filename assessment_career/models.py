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