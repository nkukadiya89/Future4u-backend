from rest_framework.routers import DefaultRouter
from .views import CoursesViewSet

courses_router = DefaultRouter()
courses_router.register(r"course", CoursesViewSet, basename="courses_router")

