from rest_framework.routers import DefaultRouter

from domain.views import DomainViewSet

domain_router = DefaultRouter()
domain_router.register("api/domains", DomainViewSet, basename="domain")
