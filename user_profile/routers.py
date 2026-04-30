from rest_framework.routers import DefaultRouter

from user_profile.internship_views import (
    InternshipApplicationViewSet,
    InternshipProfileSkillViewSet,
)
from user_profile.parent_views import ParentProfileViewSet
from user_profile.profile_views import ProfileViewSet
from user_profile.views import BusinessSettingViewSet

user_profile_router = DefaultRouter()
user_profile_router.register(
    "business-settings", BusinessSettingViewSet, basename="business_settings"
)
user_profile_router.register("profiles", ProfileViewSet, basename="profiles")
user_profile_router.register(
    "internship-skills", InternshipProfileSkillViewSet, basename="internship-skills"
)
user_profile_router.register(
    "internship-applications",
    InternshipApplicationViewSet,
    basename="internship-applications",
)
user_profile_router.register(
    "parent-profiles",
    ParentProfileViewSet,
    basename="parent-profiles",
)
