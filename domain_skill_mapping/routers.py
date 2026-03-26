from rest_framework.routers import DefaultRouter

from domain_skill_mapping.views import DomainSkillMappingViewSet

domain_skill_mapping_router = DefaultRouter()
domain_skill_mapping_router.register(
    "api/domain-skill-mappings",
    DomainSkillMappingViewSet,
    basename="domain-skill-mapping",
)

