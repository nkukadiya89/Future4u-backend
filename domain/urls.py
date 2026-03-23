from django.urls import include, path

from domain.routers import domain_router

urlpatterns = [
    path("", include(domain_router.urls)),
]
