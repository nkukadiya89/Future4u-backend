from rest_framework.routers import DefaultRouter

from city.views import CityArchiveViewSet, CityRestoreViewSet, CityViewSet

city_router = DefaultRouter()
city_router.register("city", CityViewSet, basename="city")
city_router.register("city-archive", CityArchiveViewSet, basename="city_archive")
city_router.register("city-restore", CityRestoreViewSet, basename="city_restore")
