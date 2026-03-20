from city_areas.views import (
    CityAreaArchiveViewSet,
    CityAreaRestoreViewSet,
    CityAreaViewSet,
)
from rest_framework.routers import DefaultRouter

city_area_router = DefaultRouter()
city_area_router.register("city-area", CityAreaViewSet, basename="cityarea")
city_area_router.register("city-area-archive", CityAreaArchiveViewSet, basename="cityarea_archive")
city_area_router.register("city-area-restore", CityAreaRestoreViewSet, basename="cityarea_restore")
