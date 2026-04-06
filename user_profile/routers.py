from user_profile.views import BusinessSettingViewSet
from rest_framework.routers import DefaultRouter

user_profile_router = DefaultRouter()
user_profile_router.register(
    "business-settings", BusinessSettingViewSet, basename="business_settings"
)
