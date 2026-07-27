from django.urls import path

from project_recommendation.api.views import (
    ProjectRecommendationAPIView,
    ProjectRecommendationBatchAPIView,
)

urlpatterns = [
    path(
        "api/project-recommendations/<int:suggestion_id>/",
        ProjectRecommendationAPIView.as_view(),
        name="api-project-recommendations",
    ),
    path(
        "api/project-recommendations/by-recommendation/<int:recommendation_id>/",
        ProjectRecommendationBatchAPIView.as_view(),
        name="api-project-recommendations-batch",
    ),
]
