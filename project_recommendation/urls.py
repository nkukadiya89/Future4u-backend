from django.urls import path

from project_recommendation.api.views import ProjectRecommendationAPIView

urlpatterns = [
    path(
        "api/project-recommendations/",
        ProjectRecommendationAPIView.as_view(),
        name="api-project-recommendations",
    ),
]
