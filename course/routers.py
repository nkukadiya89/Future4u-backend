from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CourseInquiryNoteViewSet, CourseInquiryViewSet, CoursesViewSet

courses_router = DefaultRouter()
courses_router.register(r"course", CoursesViewSet, basename="courses_router")
courses_router.register(
    r"course-inquiry", CourseInquiryViewSet, basename="course_inquiry"
)

course_inquiry_note_urls = [
    path(
        "course-inquiries/<int:inquiry_id>/notes/",
        CourseInquiryNoteViewSet.as_view({"get": "list", "post": "create"}),
        name="course-inquiry-notes-list",
    ),
    path(
        "course-inquiries/<int:inquiry_id>/notes/<int:pk>/",
        CourseInquiryNoteViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="course-inquiry-notes-detail",
    ),
]
