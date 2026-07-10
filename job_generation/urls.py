from django.urls import path

from job_generation.api.views import JobGenerationAPIView

urlpatterns = [
    path(
        "api/ai-job-generation/",
        JobGenerationAPIView.as_view(),
        name="api-ai-job-generation",
    ),
]
