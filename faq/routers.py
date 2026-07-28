from rest_framework.routers import DefaultRouter

from faq.views import FAQArchiveViewSet, FAQRestoreViewSet, FAQViewSet

faq_router = DefaultRouter()
faq_router.register("faq", FAQViewSet, basename="faq")
faq_router.register("faq-archive", FAQArchiveViewSet, basename="faq_archive")
faq_router.register("faq-restore", FAQRestoreViewSet, basename="faq_restore")
