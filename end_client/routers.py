from end_client.views import EndClientArchiveViewSet, EndClientRestoreViewSet, EndClientViewSet
from rest_framework.routers import DefaultRouter

end_client_router = DefaultRouter()
end_client_router.register("end-client", EndClientViewSet, basename="end_client")
end_client_router.register("end-client-archive", EndClientArchiveViewSet, basename="end_client_archive")
end_client_router.register("end-client-restore", EndClientRestoreViewSet, basename="end_client_restore")
