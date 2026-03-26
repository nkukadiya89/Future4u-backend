from business_category.views import (
    BusinessCategoryArchiveViewSet,
    BusinessCategoryRestoreViewSet,
    BusinessCategoryViewSet,
)
from rest_framework.routers import DefaultRouter

bussiness_category_router = DefaultRouter()
bussiness_category_router.register("business-category", BusinessCategoryViewSet, basename="business_category")
bussiness_category_router.register("business-category-archive", BusinessCategoryArchiveViewSet, basename="business_category_archive")
bussiness_category_router.register("business-category-restore", BusinessCategoryRestoreViewSet, basename="business_category_restore")
