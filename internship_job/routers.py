from rest_framework.routers import DefaultRouter
from .views import InternshipViewSet


internship_job_router = DefaultRouter()

internship_job_router.register(r"internship", InternshipViewSet, basename="internship_router")