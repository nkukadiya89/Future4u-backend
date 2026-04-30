from rest_framework.routers import DefaultRouter

from jobs.views import (
    JobApplicationViewSet,
    JobPreferenceViewSet,
    JobSkillViewSet,
    JobViewSet,
    SavedJobViewSet,
)

job_router = DefaultRouter()

job_router.register("jobs", JobViewSet, basename="jobs")
job_router.register("job-skills", JobSkillViewSet, basename="job-skills")
job_router.register("job-preferences", JobPreferenceViewSet, basename="job-preferences")
job_router.register(
    "job-applications", JobApplicationViewSet, basename="job-applications"
)
job_router.register("saved-jobs", SavedJobViewSet, basename="saved-jobs")
