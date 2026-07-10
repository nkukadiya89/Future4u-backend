from rest_framework.routers import DefaultRouter

from token_override.views import TokenOverrideViewSet

token_override_router = DefaultRouter()
token_override_router.register(
    "token-overrides", TokenOverrideViewSet, basename="token_override"
)
