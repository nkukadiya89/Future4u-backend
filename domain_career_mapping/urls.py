from django.urls import include, path

from domain_career_mapping.routers import domain_career_mapping_router

urlpatterns = [
    path("", include(domain_career_mapping_router.urls)),
]

