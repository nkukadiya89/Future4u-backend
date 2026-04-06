from django.urls import include, path

from skill.routers import skill_router

urlpatterns = [
    path("", include(skill_router.urls)),
]
