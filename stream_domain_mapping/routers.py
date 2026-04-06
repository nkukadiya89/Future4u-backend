from rest_framework.routers import DefaultRouter

from stream_domain_mapping.views import StreamDomainMappingViewSet

stream_domain_mapping_router = DefaultRouter()
stream_domain_mapping_router.register(
    "api/stream-domain-mappings",
    StreamDomainMappingViewSet,
    basename="stream-domain-mapping",
)
