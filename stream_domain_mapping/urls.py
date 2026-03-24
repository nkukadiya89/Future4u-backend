from django.urls import include, path

from stream_domain_mapping.routers import stream_domain_mapping_router

urlpatterns = [
    path("", include(stream_domain_mapping_router.urls)),
]

