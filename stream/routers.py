from rest_framework.routers import DefaultRouter

from stream.views import StreamViewSet

stream_router = DefaultRouter()
stream_router.register("api/streams", StreamViewSet, basename="stream")
