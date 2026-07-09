from django.urls import path

from job_generation.api.views import (
    JobGenerationAPIView,
    JobGenerationSaveView,
)

urlpatterns = [
    path(
        "api/ai-job-generation/",
        JobGenerationAPIView.as_view(),
        name="api-ai-job-generation",
    ),
    path(
        "api/ai-job-generation/save/",
        JobGenerationSaveView.as_view(),
        name="api-ai-job-generation-save",
    ),
]
