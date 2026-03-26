from django.urls import include, path

from domain_skill_mapping.routers import domain_skill_mapping_router

urlpatterns = [
    path("", include(domain_skill_mapping_router.urls)),
]

