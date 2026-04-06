from rest_framework.routers import DefaultRouter

from domain_career_mapping.views import DomainCareerMappingViewSet

domain_career_mapping_router = DefaultRouter()
domain_career_mapping_router.register(
    "api/domain-career-mappings",
    DomainCareerMappingViewSet,
    basename="domain-career-mapping",
)
