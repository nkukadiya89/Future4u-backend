from user_profile.views import BusinessSettingViewSet, StudentProfileViewSet
from rest_framework.routers import DefaultRouter

user_profile_router = DefaultRouter()
user_profile_router.register(
    "business-settings", BusinessSettingViewSet, basename="business_settings"
)
user_profile_router.register(
    "student-profile", StudentProfileViewSet, basename="student_profile"
)
