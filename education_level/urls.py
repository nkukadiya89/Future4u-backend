from django.urls import include, path

from education_level.routers import education_level_router

urlpatterns = [
    path("", include(education_level_router.urls)),
]
