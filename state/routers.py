from state.views import (
    StateArchiveViewSet,
    StateRestoreViewSet,
    StateViewSet,
)
from rest_framework.routers import DefaultRouter

state_router = DefaultRouter()
state_router.register("state", StateViewSet, basename="state")
state_router.register("state-archive", StateArchiveViewSet, basename="state_archive")
state_router.register("state-restore", StateRestoreViewSet, basename="state_restore")
