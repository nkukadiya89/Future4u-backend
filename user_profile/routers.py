from user_profile.views import (
    BusinessSettingViewSet,
    ChildProfileViewSet,
    CorporateGalleryViewSet,
    CorporateProfileViewSet,
    InstituteGalleryViewSet,
    InstituteProfileViewSet,
    ParentProfileViewSet,
    ProfessionalProfileViewSet,
    SchoolCollegeGalleryViewSet,
    SchoolCollegeProfileViewSet,
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
    "api/parent-profile/children",
    ChildProfileViewSet,
    basename="parent_children",
)
user_profile_router.register(
    "api/parent-profile", ParentProfileViewSet, basename="parent_profile"
)
user_profile_router.register(
    "api/school-college-profile/gallery",
    SchoolCollegeGalleryViewSet,
    basename="school_college_gallery",
)
user_profile_router.register(
    "api/school-college-profile",
    SchoolCollegeProfileViewSet,
    basename="school_college_profile",
)
user_profile_router.register(
    "api/corporate-profile/gallery",
    CorporateGalleryViewSet,
    basename="corporate_gallery",
)
user_profile_router.register(
    "api/corporate-profile",
    CorporateProfileViewSet,
    basename="corporate_profile",
)
user_profile_router.register(
    "api/institute-profile/gallery",
    InstituteGalleryViewSet,
    basename="institute_gallery",
)
user_profile_router.register(
    "api/institute-profile",
    InstituteProfileViewSet,
    basename="institute_profile",
)
