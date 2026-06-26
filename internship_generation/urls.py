from django.urls import path

from internship_generation.api.views import InternshipGenerationAPIView

urlpatterns = [
    path(
        "api/ai-internship-generation/",
        InternshipGenerationAPIView.as_view(),
        name="api-ai-internship-generation",
    ),
]
