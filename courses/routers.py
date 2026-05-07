from rest_framework.routers import DefaultRouter

from courses.course_enrollment_views import CourseEnrollmentViewSet
from courses.course_outcome_views import CourseOutcomeViewSet
from courses.course_reference_views import ProfileCoursePreferenceViewSet
from courses.course_review_views import CourseReviewViewSet
from courses.course_views import CourseViewSet

course_router = DefaultRouter()

course_router.register("courses", CourseViewSet, basename="courses")
course_router.register(
    "course-enrollments", CourseEnrollmentViewSet, basename="course-enrollments"
)
course_router.register(
    "course-outcomes", CourseOutcomeViewSet, basename="course-outcomes"
)
course_router.register("course-reviews", CourseReviewViewSet, basename="course-reviews")
course_router.register(
    "course-preferences", ProfileCoursePreferenceViewSet, basename="course-preferences"
)
