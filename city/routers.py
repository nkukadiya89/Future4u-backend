from city.views import (
    CityArchiveViewSet,
    CityRestoreViewSet,
    CityViewSet,
)
from rest_framework.routers import DefaultRouter

city_router = DefaultRouter()
city_router.register("city", CityViewSet, basename="city")
city_router.register("city-archive", CityArchiveViewSet, basename="city_archive")
city_router.register("city-restore", CityRestoreViewSet, basename="city_restore")
