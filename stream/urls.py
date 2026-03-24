from django.urls import include, path

from stream.routers import stream_router

urlpatterns = [
    path("", include(stream_router.urls)),
]
