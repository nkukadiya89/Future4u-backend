from user_profile.views import (
    BusinessSettingViewSet,
    ParentProfileViewSet,
    ProfessionalProfileViewSet,
    StudentProfileViewSet,
    UserProfileViewSet,
)
from rest_framework.routers import DefaultRouter

user_profile_router = DefaultRouter()
user_profile_router.register("api/profile", UserProfileViewSet, basename="profile")
user_profile_router.register(
    "business-settings", BusinessSettingViewSet, basename="business_settings"
)
user_profile_router.register(
    "api/student-profile", StudentProfileViewSet, basename="student_profile"
)
user_profile_router.register(
    "api/professional-profile",
    ProfessionalProfileViewSet,
    basename="professional_profile",
)
user_profile_router.register(
    "api/parent-profile", ParentProfileViewSet, basename="parent_profile"
)

from user_profile.internship_views import (
    InternshipApplicationViewSet,
)
from user_profile.views import BusinessSettingViewSet

# from user_profile.parent_views import ParentProfileViewSet
# from user_profile.profile_views import ProfileViewSet
# user_profile_router.register("profiles", ProfileViewSet, basename="profiles")
user_profile_router.register(
    "internship-applications",
    InternshipApplicationViewSet,
    basename="internship-applications",
)
