from rest_framework.routers import DefaultRouter
from .views import InternshipViewSet, InternshipApplicationViewSet
from .jobs_views import JobViewSet, JobApplicationViewSet


internship_job_router = DefaultRouter()

internship_job_router.register(
    r"internship", InternshipViewSet, basename="internship_router"
)
internship_job_router.register(
    r"internship_application",
    InternshipApplicationViewSet,
    basename="internship_application_router",
)
internship_job_router.register(r"job", JobViewSet, basename="job_router")
internship_job_router.register(
    r"job_application", JobApplicationViewSet, basename="job_application_router"
)
