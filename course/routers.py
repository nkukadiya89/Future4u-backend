from rest_framework.routers import DefaultRouter

from .views import CourseInquiryViewSet, CoursesViewSet

courses_router = DefaultRouter()
courses_router.register(r"course", CoursesViewSet, basename="courses_router")
courses_router.register(
    r"course-inquiry", CourseInquiryViewSet, basename="course_inquiry"
)
