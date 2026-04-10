from rest_framework.routers import DefaultRouter

from language_master.views import LanguageViewSet

language_router = DefaultRouter()
language_router.register("api/languages", LanguageViewSet, basename="language")
