from rest_framework.routers import DefaultRouter
from .views import InternshipViewSet,InternshipApplicationViewSet


internship_job_router = DefaultRouter()

internship_job_router.register(r"internship", InternshipViewSet, basename="internship_router")
internship_job_router.register(r"internship_application", InternshipApplicationViewSet, basename="internship_application_router")
