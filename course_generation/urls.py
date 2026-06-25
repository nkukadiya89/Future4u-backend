from django.urls import path

from course_generation.api.views import CourseGenerationAPIView

urlpatterns = [
    path(
        "api/ai-course-generation/",
        CourseGenerationAPIView.as_view(),
        name="api-ai-course-generation",
    ),
]
