from rest_framework.routers import DefaultRouter

from education_level.views import EducationLevelViewSet

education_level_router = DefaultRouter()
education_level_router.register("api/education-levels", EducationLevelViewSet, basename="education-level")
