from django.urls import include, path
from rest_framework.routers import DefaultRouter

from company.api.views import CompanyV1ViewSet

router = DefaultRouter()
router.register("", CompanyV1ViewSet, basename="company-v1")

urlpatterns = [
    path("", include(router.urls)),
]
