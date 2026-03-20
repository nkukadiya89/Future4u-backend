from business_category.views import (
    BusinessCategoryViewSet,
)
from rest_framework.routers import DefaultRouter

bussiness_category_router = DefaultRouter()
bussiness_category_router.register("business-category", BusinessCategoryViewSet, basename="business_category")
