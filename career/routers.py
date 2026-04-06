from rest_framework.routers import DefaultRouter

from career.views import CareerViewSet

career_router = DefaultRouter()
career_router.register("api/careers", CareerViewSet, basename="career")
