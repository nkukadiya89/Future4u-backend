from country.views import (
    CountryArchiveViewSet,
    CountryRestoreViewSet,
    CountryViewSet,
)
from rest_framework.routers import DefaultRouter

country_router = DefaultRouter()
country_router.register("country", CountryViewSet, basename="country")
country_router.register("country-archive", CountryArchiveViewSet, basename="country_archive")
country_router.register("country-restore", CountryRestoreViewSet, basename="country_restore")
