from django.urls import include, path

from assessment.routers import assessment_router

urlpatterns = [
    path("", include(assessment_router.urls)),
]
