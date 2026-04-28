from user_profile.views import (
    BusinessSettingViewSet,
    ProfessionalProfileViewSet,
    StudentProfileViewSet,
    UserProfileViewSet,
)
from rest_framework.routers import DefaultRouter

user_profile_router = DefaultRouter()
user_profile_router.register(
    "api/profile", UserProfileViewSet, basename="profile"
)
user_profile_router.register(
    "business-settings", BusinessSettingViewSet, basename="business_settings"
)
user_profile_router.register(
    "api/student-profile", StudentProfileViewSet, basename="student_profile"
)
user_profile_router.register(
    "api/professional-profile", ProfessionalProfileViewSet, basename="professional_profile"
)
