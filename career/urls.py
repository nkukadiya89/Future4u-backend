from django.urls import include, path

from career.routers import career_router

urlpatterns = [
    path("", include(career_router.urls)),
]
